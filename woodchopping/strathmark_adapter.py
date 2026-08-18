# -*- coding: utf-8 -*-
"""
STRATHEX <-> STRATHMARK adapter.

This module is the single production boundary between STRATHEX's DataFrame-
based tournament application and STRATHMARK's typed prediction engine.  It
translates records, executes the prediction stack, delegates mark arithmetic,
and exposes small compatibility facades for persistence and simulation.

No tournament workflow or user-interface policy belongs here.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any, Dict, List, Mapping, Optional

import pandas as pd
import strathmark.variance as _sm_variance
from strathmark import (
    CompetitorRecord,
    HandicapCalculator,
    HistoricalResult,
    PredictionResult,
    ResultStore,
    WoodProfile,
    get_all_predictions,
    select_best_prediction,
)
from strathmark.config import llm_config
from strathmark.fairness import (
    get_ai_assessment_of_handicaps as _sm_assess_handicaps,
)
from strathmark.fairness import (
    get_championship_race_analysis as _sm_championship_analysis,
)
from strathmark.fairness import (
    simulate_and_assess_handicaps as _sm_simulate_and_assess,
)
from strathmark.predictor import MLModel

_log = logging.getLogger(__name__)
_ML_MODEL_CACHE: Dict[tuple, Optional[MLModel]] = {}


# ---------------------------------------------------------------------------
# Normalisation helpers
# ---------------------------------------------------------------------------


def _name_key(value: Any) -> str:
    """Return a stable, case-insensitive key for a competitor name."""
    if value is None or pd.isna(value):
        return ""
    return str(value).strip().casefold()


def _clean_gender(value: Any) -> Optional[str]:
    """Normalise roster gender values to STRATHMARK's ``M`` / ``F`` encoding."""
    if value is None or pd.isna(value):
        return None
    text = str(value).strip().upper()
    if text in {"M", "MALE", "MEN", "MAN"}:
        return "M"
    if text in {"F", "FEMALE", "WOMEN", "WOMAN"}:
        return "F"
    return None


def _clean_optional_text(value: Any) -> Optional[str]:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    return text or None


def enrich_results_with_roster(
    results_df: Optional[pd.DataFrame],
    roster_df: Optional[pd.DataFrame],
) -> pd.DataFrame:
    """
    Fill historical-result gender values from the competitor roster.

    STRATHMARK's ML feature schema includes gender.  The Results sheet stores
    performance observations while the Competitor sheet stores gender, so the
    two sources must be joined before model training.  Existing valid result
    values are preserved and the input DataFrames are never mutated.
    """
    results = results_df.copy() if isinstance(results_df, pd.DataFrame) else pd.DataFrame()
    if results.empty or roster_df is None or roster_df.empty:
        return results

    roster = roster_df.copy()
    roster.columns = [str(col).strip() for col in roster.columns]
    roster.rename(
        columns={
            "Name": "competitor_name",
            "name": "competitor_name",
            "Competitor Name": "competitor_name",
            "Gender": "gender",
        },
        inplace=True,
    )

    if "competitor_name" not in results.columns or not {
        "competitor_name",
        "gender",
    }.issubset(roster.columns):
        return results

    gender_by_name: Dict[str, str] = {}
    for _, row in roster[["competitor_name", "gender"]].iterrows():
        key = _name_key(row.get("competitor_name"))
        gender = _clean_gender(row.get("gender"))
        if key and gender:
            gender_by_name[key] = gender

    if not gender_by_name:
        return results

    mapped = results["competitor_name"].map(lambda value: gender_by_name.get(_name_key(value)))
    if "gender" not in results.columns:
        results["gender"] = mapped
    else:
        existing = results["gender"].map(_clean_gender)
        results["gender"] = existing.where(existing.notna(), mapped)

    return results


def build_gender_map(
    competitor_df: Optional[pd.DataFrame],
    results_df: Optional[pd.DataFrame] = None,
) -> Dict[str, str]:
    """Build an exact-name -> gender map for current competitor records."""
    by_key: Dict[str, str] = {}
    display_name_by_key: Dict[str, str] = {}

    for frame in (competitor_df, results_df):
        if frame is None or frame.empty or "competitor_name" not in frame.columns:
            continue
        if "gender" not in frame.columns:
            continue

        for _, row in frame[["competitor_name", "gender"]].iterrows():
            name = _clean_optional_text(row.get("competitor_name"))
            gender = _clean_gender(row.get("gender"))
            key = _name_key(name)
            if key and gender:
                by_key[key] = gender
                display_name_by_key.setdefault(key, name or key)

    return {display_name_by_key[key]: value for key, value in by_key.items()}


# ---------------------------------------------------------------------------
# Build STRATHMARK input objects
# ---------------------------------------------------------------------------


def build_competitor_records(
    competitor_names: List[str],
    results_df: pd.DataFrame,
    division_map: Optional[Dict[str, str]] = None,
    tournament_results: Optional[Dict[str, float]] = None,
    gender_map: Optional[Dict[str, str]] = None,
) -> List[CompetitorRecord]:
    """
    Convert STRATHEX historical rows into STRATHMARK ``CompetitorRecord`` objects.

    ``tournament_results`` retains STRATHEX's established same-wood policy:
    once an earlier-round time exists it receives the documented 97% weight.
    STRATHMARK expresses that policy through ``num_tournament_rounds=4``.
    """
    if results_df is None:
        results_df = pd.DataFrame()

    df = results_df.copy()
    df.columns = [str(col).strip().lower() for col in df.columns]
    df.rename(
        columns={
            "event_code": "event",
            "time": "raw_time",
            "actual_time": "raw_time",
            "diameter_mm": "size_mm",
            "diameter": "size_mm",
            "species_code": "species",
            "result_date": "date",
        },
        inplace=True,
    )

    division_by_key = {_name_key(name): value for name, value in (division_map or {}).items()}
    gender_by_key = {
        _name_key(name): _clean_gender(value) for name, value in (gender_map or {}).items()
    }
    tournament_by_key = {
        _name_key(name): value for name, value in (tournament_results or {}).items()
    }

    records: List[CompetitorRecord] = []
    for name in competitor_names:
        key = _name_key(name)
        if "competitor_name" in df.columns:
            mask = df["competitor_name"].map(_name_key) == key
            comp_rows = df[mask]
        else:
            comp_rows = df.iloc[0:0]

        history: List[HistoricalResult] = []
        for _, row in comp_rows.iterrows():
            try:
                raw_time = float(row.get("raw_time", float("nan")))
                if pd.isna(raw_time) or raw_time <= 0:
                    continue

                event_code = (_clean_optional_text(row.get("event")) or "SB").upper()
                species = _clean_optional_text(row.get("species")) or "Unknown"

                size_value = row.get("size_mm", 300.0)
                size_mm = float(size_value)
                if pd.isna(size_mm) or size_mm <= 0:
                    size_mm = 300.0

                quality_value = row.get("quality", 5)
                quality = (
                    int(float(quality_value))
                    if quality_value is not None and not pd.isna(quality_value)
                    else 5
                )
                quality = max(1, min(10, quality))

                result_date = None
                date_value = row.get("date")
                if date_value is not None and not pd.isna(date_value):
                    try:
                        if hasattr(date_value, "date") and callable(date_value.date):
                            result_date = date_value.date()
                        elif isinstance(date_value, str) and date_value.strip():
                            result_date = date.fromisoformat(date_value.strip()[:10])
                    except (TypeError, ValueError):
                        result_date = None
                if result_date is not None and pd.isna(result_date):
                    result_date = None

                field_strength = row.get("field_strength")
                if field_strength is not None and not pd.isna(field_strength):
                    field_strength = float(field_strength)
                else:
                    field_strength = None

                history.append(
                    HistoricalResult(
                        event_code=event_code,
                        time_seconds=raw_time,
                        species=species,
                        diameter_mm=size_mm,
                        quality=quality,
                        result_date=result_date,
                        heat_id=_clean_optional_text(row.get("heat_id")),
                        field_strength=field_strength,
                    )
                )
            except (TypeError, ValueError, OverflowError):
                continue

        gender = gender_by_key.get(key)
        if gender is None and "gender" in comp_rows.columns:
            for value in comp_rows["gender"]:
                gender = _clean_gender(value)
                if gender:
                    break

        tournament_time = tournament_by_key.get(key)
        if tournament_time is not None:
            try:
                tournament_time = float(tournament_time)
                if pd.isna(tournament_time) or tournament_time <= 0:
                    tournament_time = None
            except (TypeError, ValueError):
                tournament_time = None

        records.append(
            CompetitorRecord(
                name=str(name),
                history=history,
                division=division_by_key.get(key),
                tournament_time=tournament_time,
                num_tournament_rounds=4 if tournament_time is not None else 1,
                gender=gender,
            )
        )

    return records


def build_wood_profile(species: str, diameter: float, quality: int) -> WoodProfile:
    """Create the STRATHMARK wood value object at the integration boundary."""
    return WoodProfile(
        species=str(species),
        diameter_mm=float(diameter),
        quality=max(1, min(10, int(quality))),
    )


# ---------------------------------------------------------------------------
# Prediction and mark calculation
# ---------------------------------------------------------------------------


def _frame_fingerprint(frame: Optional[pd.DataFrame]) -> tuple:
    """Return a deterministic in-process fingerprint for model-cache invalidation."""
    if frame is None or frame.empty:
        return ("empty",)

    try:
        row_hash = pd.util.hash_pandas_object(
            frame,
            index=True,
            categorize=True,
        )
        value_hash = int(row_hash.sum())
    except (TypeError, ValueError):
        value_hash = hash(frame.to_csv(index=True))

    return (
        tuple(str(column) for column in frame.columns),
        tuple(str(dtype) for dtype in frame.dtypes),
        frame.shape,
        value_hash,
    )


def _train_ml_model(
    results_df: Optional[pd.DataFrame],
    wood_df: Optional[pd.DataFrame],
) -> Optional[MLModel]:
    """Train or reuse the ML model for an unchanged historical dataset."""
    if results_df is None or results_df.empty:
        return None

    cache_key = (
        _frame_fingerprint(results_df),
        _frame_fingerprint(wood_df),
    )
    if cache_key in _ML_MODEL_CACHE:
        return _ML_MODEL_CACHE[cache_key]

    model = MLModel()
    try:
        trained_model = model if model.train(results_df, wood_df) else None
    except Exception as exc:
        _log.warning(
            "STRATHMARK ML training failed; continuing without ML: %s",
            exc,
        )
        trained_model = None

    # Keep only the latest dataset.  Results are re-fingerprinted after every
    # workbook reload, so newly entered times invalidate the cached model.
    _ML_MODEL_CACHE.clear()
    _ML_MODEL_CACHE[cache_key] = trained_model
    return trained_model


def _prediction_to_dict(
    prediction: Optional[PredictionResult],
    *,
    unavailable_message: str = "Not available",
) -> Dict[str, Any]:
    if prediction is None:
        return {
            "time": None,
            "confidence": None,
            "explanation": None,
            "error": unavailable_message,
            "scaled": False,
            "original_diameter": None,
            "scaling_warning": None,
            "tournament_weighted": False,
            "std_dev": None,
            "metadata": None,
        }

    metadata = dict(prediction.metadata or {})
    scaling_metadata = metadata.get("scaling_metadata")
    scaled = bool(metadata.get("scaled", metadata.get("was_scaled", False)))
    original_diameter = metadata.get("original_diameter")
    scaling_warning = metadata.get("scaling_warning") or metadata.get("warning_message")

    if scaling_metadata is not None:
        scaled = bool(
            getattr(scaling_metadata, "was_scaled", scaled)
            if not isinstance(scaling_metadata, Mapping)
            else scaling_metadata.get("was_scaled", scaled)
        )
        if isinstance(scaling_metadata, Mapping):
            original_diameter = scaling_metadata.get("original_diameter", original_diameter)
            scaling_warning = scaling_metadata.get("warning_message", scaling_warning)
        else:
            original_diameter = getattr(scaling_metadata, "original_diameter", original_diameter)
            scaling_warning = getattr(scaling_metadata, "warning_message", scaling_warning)

    return {
        "time": float(prediction.value),
        "confidence": prediction.confidence,
        "explanation": prediction.explanation,
        "error": None,
        "scaled": scaled,
        "original_diameter": original_diameter,
        "scaling_warning": scaling_warning,
        "tournament_weighted": bool(metadata.get("tournament_weighted", False)),
        "std_dev": metadata.get("std_dev"),
        "metadata": metadata,
    }


def _display_method_name(method: Optional[str]) -> str:
    names = {
        "manual": "Manual",
        "llm": "LLM",
        "ml": "ML",
        "baseline": "Baseline",
        "panel": "Panel",
        "championship": "Championship",
    }
    key = str(method or "").strip().lower()
    return names.get(key, str(method or "Unknown"))


def mark_results_to_dicts(
    mark_results,
    competitor_records: List[CompetitorRecord],
    wood: WoodProfile,
    event_code: str,
    results_df: Optional[pd.DataFrame] = None,
    ollama_url: str = "http://localhost:11434",
    predictions_by_name: Optional[Dict[str, Dict[str, Optional[PredictionResult]]]] = None,
    selected_by_name: Optional[Dict[str, PredictionResult]] = None,
) -> List[Dict[str, Any]]:
    """
    Convert STRATHMARK results to STRATHEX's established dictionary contract.

    When exact prediction dictionaries are supplied, the values displayed to the
    judge are the same objects used for method selection and mark calculation.
    This avoids the former second prediction pass and its possible divergence.
    """
    del competitor_records, wood, event_code, results_df, ollama_url

    predictions_by_name = predictions_by_name or {}
    selected_by_name = selected_by_name or {}
    output: List[Dict[str, Any]] = []

    for mark_result in mark_results:
        raw_predictions = predictions_by_name.get(mark_result.name, {})
        predictions = {
            method: _prediction_to_dict(raw_predictions.get(method))
            for method in ("manual", "llm", "ml", "baseline", "panel")
        }

        selected = selected_by_name.get(mark_result.name)
        if selected is None:
            selected = PredictionResult(
                value=float(mark_result.predicted_time),
                confidence=mark_result.confidence,
                method=mark_result.method_used,
                explanation=mark_result.explanation,
            )
            method_key = str(selected.method).strip().lower()
            predictions[method_key] = _prediction_to_dict(selected)

        method_used = _display_method_name(selected.method)
        std_dev = float(getattr(mark_result, "std_dev", 3.0))

        output.append(
            {
                "name": mark_result.name,
                "mark": int(mark_result.mark),
                "predicted_time": float(mark_result.predicted_time),
                "method_used": method_used,
                "confidence": selected.confidence,
                "explanation": selected.explanation,
                "predictions": predictions,
                "performance_std_dev": std_dev,
                "std_dev": std_dev,
            }
        )

    return output


def calculate_handicap_results(
    competitor_records: List[CompetitorRecord],
    wood: WoodProfile,
    event_code: str,
    results_df: Optional[pd.DataFrame],
    wood_df: Optional[pd.DataFrame] = None,
    tournament_results: Optional[Dict[str, float]] = None,
    ollama_url: str = "http://localhost:11434",
) -> List[Dict[str, Any]]:
    """
    Run all prediction methods once, select by expected error, then delegate
    unchanged mark arithmetic and variance calculation to STRATHMARK.

    The manual-override channel is used internally only to feed the already
    selected prediction value into ``HandicapCalculator``.  The returned
    STRATHEX records retain the real selected method and explanation.
    """
    if not competitor_records:
        return []

    event_code = str(event_code).strip().upper()
    ml_model = _train_ml_model(results_df, wood_df)
    llm_client = {
        "url": ollama_url,
        "model": llm_config.PREDICTION_MODEL,
        "timeout": llm_config.TIMEOUT_SECONDS,
    }

    predictions_by_name: Dict[str, Dict[str, Optional[PredictionResult]]] = {}
    selected_by_name: Dict[str, PredictionResult] = {}

    for record in competitor_records:
        try:
            all_predictions = get_all_predictions(
                record,
                wood,
                event_code,
                wood_data_df=wood_df,
                results_df=results_df,
                ml_model=ml_model,
                llm_client=llm_client,
            )
        except Exception as first_error:
            _log.warning(
                "Prediction comparison failed for %s with LLM enabled; "
                "retrying deterministic methods only: %s",
                record.name,
                first_error,
            )
            all_predictions = get_all_predictions(
                record,
                wood,
                event_code,
                wood_data_df=wood_df,
                results_df=results_df,
                ml_model=ml_model,
                llm_client=None,
            )

        selected = select_best_prediction(all_predictions)
        predictions_by_name[record.name] = all_predictions
        selected_by_name[record.name] = selected

    selected_values = {name: prediction.value for name, prediction in selected_by_name.items()}

    # Let STRATHMARK retain sole ownership of sorting, gap rounding, mark bounds,
    # and per-competitor performance variance.
    calculator = HandicapCalculator(
        ollama_url=ollama_url,
        wood_df=wood_df,
        results_df=None,
    )
    mark_results = calculator.calculate(
        competitors=competitor_records,
        wood=wood,
        event_code=event_code,
        tournament_results=tournament_results or {},
        manual_overrides=selected_values,
    )

    return mark_results_to_dicts(
        mark_results,
        competitor_records=competitor_records,
        wood=wood,
        event_code=event_code,
        results_df=results_df,
        ollama_url=ollama_url,
        predictions_by_name=predictions_by_name,
        selected_by_name=selected_by_name,
    )


# ---------------------------------------------------------------------------
# Persistence boundary
# ---------------------------------------------------------------------------


def create_result_store() -> ResultStore:
    """Create STRATHMARK's persistent result store through the adapter."""
    return ResultStore()


def record_round_results(
    round_object: Dict[str, Any],
    wood_selection: Dict[str, Any],
    store: ResultStore,
) -> int:
    """Write a completed tournament round to the STRATHMARK result store."""
    actual_results = round_object.get("actual_results") or round_object.get("results") or {}
    if not actual_results:
        return 0

    round_name = round_object.get("round_name", "")
    event_code = str(wood_selection.get("event", "SB")).strip().upper()
    species = str(wood_selection.get("species", "Unknown"))
    diameter_mm = float(wood_selection.get("size_mm", 300))
    quality = int(wood_selection.get("quality", 5))
    heat_id = round_name.replace(" ", "-").replace("/", "-") if round_name else ""

    inserted = 0
    for competitor_name, time_seconds in actual_results.items():
        if time_seconds is None:
            continue
        try:
            if store.record_result(
                competitor_name=str(competitor_name),
                event_code=event_code,
                time_seconds=float(time_seconds),
                species=species,
                diameter_mm=diameter_mm,
                quality=quality,
                heat_id=heat_id,
            ):
                inserted += 1
        except Exception as exc:
            _log.warning("Could not persist result for %s: %s", competitor_name, exc)

    return inserted


def migrate_excel_to_store(results_df: pd.DataFrame, store: ResultStore) -> int:
    """Idempotently import the Excel history into STRATHMARK's result store."""
    if results_df is None or results_df.empty:
        return 0
    return store.import_from_dataframe(results_df, skip_duplicates=True)


# ---------------------------------------------------------------------------
# Simulation and fairness compatibility facades
# ---------------------------------------------------------------------------


def get_competitor_variance_seconds(comp: Dict[str, Any]) -> float:
    """Isolate the pinned STRATHMARK private variance helper in one boundary."""
    return float(_sm_variance._get_competitor_variance_seconds(comp))


def run_monte_carlo_simulation_engine(
    competitors_with_marks: List[Dict[str, Any]],
    **kwargs,
) -> Dict[str, Any]:
    return _sm_variance.run_monte_carlo_simulation(
        competitors_with_marks,
        **kwargs,
    )


def get_ai_assessment_engine(analysis: Dict[str, Any]) -> str:
    return _sm_assess_handicaps(analysis)


def get_championship_analysis_engine(
    analysis: Dict[str, Any],
    predictions: List[Dict],
) -> str:
    return _sm_championship_analysis(analysis, predictions)


def simulate_and_assess_engine(
    competitors_with_marks: List[Dict[str, Any]],
    *,
    num_simulations: Optional[int] = None,
    show: bool = True,
):
    return _sm_simulate_and_assess(
        competitors_with_marks,
        num_simulations=num_simulations,
        show=show,
    )
