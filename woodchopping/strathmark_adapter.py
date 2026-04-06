# -*- coding: utf-8 -*-
"""
STRATHEX <-> STRATHMARK Adapter
=================================

Translates between STRATHEX's DataFrame-based world and STRATHMARK's typed
objects (CompetitorRecord, WoodProfile, HistoricalResult, MarkResult).

This is the only file in STRATHEX that imports from strathmark. All other
STRATHEX modules that need handicap calculations go through this adapter.

Public functions:
    build_competitor_records()     -- results_df rows -> List[CompetitorRecord]
    mark_results_to_dicts()        -- List[MarkResult] -> STRATHEX handicap dicts
    record_round_results()         -- tournament round -> ResultStore
    migrate_excel_to_store()       -- one-time import of woodchopping.xlsx history
"""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional

import pandas as pd
from strathmark import (
    CompetitorRecord,
    HistoricalResult,
    WoodProfile,
    get_all_predictions,
)
from strathmark.store import ResultStore
from strathmark.variance import estimate_competitor_std_dev

# ---------------------------------------------------------------------------
# Build CompetitorRecord objects from STRATHEX results_df
# ---------------------------------------------------------------------------


def build_competitor_records(
    competitor_names: List[str],
    results_df: pd.DataFrame,
    division_map: Optional[Dict[str, str]] = None,
    tournament_results: Optional[Dict[str, float]] = None,
) -> List[CompetitorRecord]:
    """
    Convert STRATHEX results_df rows into CompetitorRecord objects.

    Args:
        competitor_names: Names of competitors in this heat/round (preserves order).
        results_df: Historical results DataFrame with STRATHEX normalized columns:
                    competitor_name, event, raw_time, species, size_mm, quality,
                    date (optional), heat_id (optional).
        division_map: Optional {name: division} for panel mark fallback.
        tournament_results: Optional {name: actual_time} from current tournament
                            (same-wood 97% weighting for semis/finals).

    Returns:
        List of CompetitorRecord, one per name, in input order.
    """
    if results_df is None:
        results_df = pd.DataFrame()

    # Normalise column names defensively
    df = results_df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]
    _rename = {
        "event": "event",  # already correct
        "event_code": "event",
        "time": "raw_time",
        "actual_time": "raw_time",
        "diameter_mm": "size_mm",
        "diameter": "size_mm",
    }
    df.rename(columns=_rename, inplace=True)

    records = []
    for name in competitor_names:
        # Filter rows for this competitor
        mask = (
            df["competitor_name"].astype(str).str.strip().str.lower() == name.strip().lower()
            if "competitor_name" in df.columns
            else pd.Series(False, index=df.index)
        )
        comp_rows = df[mask]

        history: List[HistoricalResult] = []
        for _, row in comp_rows.iterrows():
            try:
                raw_time = float(row.get("raw_time", float("nan")))
                if pd.isna(raw_time) or raw_time <= 0:
                    continue
                event_code = str(row.get("event", "SB")).strip().upper()
                species = str(row.get("species", "Unknown")).strip()
                size_mm = float(row.get("size_mm", 300))
                quality = int(float(row.get("quality", 5))) if not pd.isna(row.get("quality", 5)) else 5

                # Parse date
                rd = None
                date_val = row.get("date")
                if date_val is not None and not (isinstance(date_val, float) and pd.isna(date_val)):
                    try:
                        if hasattr(date_val, "date"):
                            rd = date_val.date()
                        elif isinstance(date_val, str) and date_val.strip():
                            rd = date.fromisoformat(date_val.strip()[:10])
                    except (ValueError, TypeError):
                        rd = None

                heat_id = str(row.get("heat_id", "") or "")

                history.append(
                    HistoricalResult(
                        event_code=event_code,
                        time_seconds=raw_time,
                        species=species,
                        diameter_mm=size_mm,
                        quality=quality,
                        result_date=rd,
                        heat_id=heat_id if heat_id else None,
                    )
                )
            except (ValueError, TypeError):
                continue

        division = (division_map or {}).get(name)
        tournament_time = (tournament_results or {}).get(name)

        records.append(
            CompetitorRecord(
                name=name,
                history=history,
                division=division,
                tournament_time=tournament_time,
            )
        )

    return records


# ---------------------------------------------------------------------------
# Convert MarkResult -> STRATHEX handicap dicts
# ---------------------------------------------------------------------------


def mark_results_to_dicts(
    mark_results,
    competitor_records: List[CompetitorRecord],
    wood: WoodProfile,
    event_code: str,
    results_df: Optional[pd.DataFrame] = None,
    ollama_url: str = "http://localhost:11434",
) -> List[Dict[str, Any]]:
    """
    Convert STRATHMARK MarkResult objects to the dict format that STRATHEX
    UI code expects from calculate_ai_enhanced_handicaps().

    Preserves the 3-column prediction display by re-running get_all_predictions()
    for each competitor (same data that HandicapCalculator computed internally).

    Args:
        mark_results: List[MarkResult] from HandicapCalculator.calculate().
        competitor_records: The CompetitorRecord objects used for calculation
                            (same order as mark_results).
        wood: WoodProfile used for this event.
        event_code: 'SB' or 'UH'.
        results_df: Optional historical DataFrame for std_dev estimation.
        ollama_url: Ollama API base URL for LLM predictions.

    Returns:
        List of dicts with keys:
            name, mark, predicted_time, method_used, confidence, explanation,
            predictions (3-column dict), performance_std_dev.
    """
    # Build a name -> CompetitorRecord lookup
    record_lookup: Dict[str, CompetitorRecord] = {r.name: r for r in competitor_records}

    out = []
    for mr in mark_results:
        record = record_lookup.get(mr.name)

        # Re-run all predictions for 3-column display
        if record is not None:
            try:
                all_preds_sm = get_all_predictions(
                    record,
                    wood,
                    event_code,
                    llm_client={"url": ollama_url + "/api/generate", "model": None, "timeout": 120},
                )
                # Convert PredictionResult objects to the nested-dict format STRATHEX UI expects
                predictions = {}
                for method_key, pred_result in all_preds_sm.items():
                    if pred_result is not None:
                        predictions[method_key] = {
                            "time": pred_result.value,
                            "confidence": pred_result.confidence,
                            "explanation": pred_result.explanation,
                            "error": None,
                            "tournament_weighted": pred_result.metadata.get("tournament_weighted", False)
                            if pred_result.metadata
                            else False,
                        }
                    else:
                        predictions[method_key] = {
                            "time": None,
                            "confidence": None,
                            "explanation": None,
                            "error": "Not available",
                            "tournament_weighted": False,
                        }
            except Exception:
                # Fallback: minimal predictions dict from MarkResult
                predictions = {
                    mr.method_used: {
                        "time": mr.predicted_time,
                        "confidence": mr.confidence,
                        "explanation": mr.explanation,
                        "error": None,
                        "tournament_weighted": False,
                    }
                }
        else:
            predictions = {}

        # Estimate performance std_dev for Monte Carlo
        performance_std_dev = None
        if results_df is not None and not results_df.empty:
            try:
                std_val, _ = estimate_competitor_std_dev(mr.name, event_code, results_df)
                performance_std_dev = float(std_val)
            except Exception:
                pass

        out.append(
            {
                "name": mr.name,
                "mark": mr.mark,
                "predicted_time": mr.predicted_time,
                "method_used": mr.method_used,
                "confidence": mr.confidence,
                "explanation": mr.explanation,
                "predictions": predictions,
                "performance_std_dev": performance_std_dev,
            }
        )

    return out


# ---------------------------------------------------------------------------
# Write round results to ResultStore
# ---------------------------------------------------------------------------


def record_round_results(
    round_object: Dict[str, Any],
    wood_selection: Dict[str, Any],
    store: ResultStore,
) -> int:
    """
    Write results from a completed tournament round into the ResultStore.

    Safe to call multiple times — INSERT OR IGNORE handles duplicates.

    Args:
        round_object: Tournament round dict with 'actual_results' {name: time}
                      and 'round_name'.
        wood_selection: {'species': str, 'size_mm': float, 'quality': int, 'event': str}
        store: Open ResultStore instance.

    Returns:
        Number of new rows inserted.
    """
    actual_results = round_object.get("actual_results") or round_object.get("results") or {}
    if not actual_results:
        return 0

    round_name = round_object.get("round_name", "")
    event_code = str(wood_selection.get("event", "SB")).strip().upper()
    species = str(wood_selection.get("species", "Unknown"))
    diameter_mm = float(wood_selection.get("size_mm", 300))
    quality = int(wood_selection.get("quality", 5))

    # Build heat_id from round_name: strip spaces/special chars
    heat_id = round_name.replace(" ", "-").replace("/", "-") if round_name else ""

    inserted = 0
    for competitor_name, time_seconds in actual_results.items():
        if time_seconds is None:
            continue
        try:
            ok = store.record_result(
                competitor_name=str(competitor_name),
                event_code=event_code,
                time_seconds=float(time_seconds),
                species=species,
                diameter_mm=diameter_mm,
                quality=quality,
                heat_id=heat_id,
            )
            if ok:
                inserted += 1
        except Exception:
            continue

    return inserted


# ---------------------------------------------------------------------------
# One-time migration of woodchopping.xlsx history -> ResultStore
# ---------------------------------------------------------------------------


def migrate_excel_to_store(
    results_df: pd.DataFrame,
    store: ResultStore,
) -> int:
    """
    Bulk-import all existing Excel results into the ResultStore.

    Uses INSERT OR IGNORE so this is idempotent — safe to call on every startup.

    Args:
        results_df: DataFrame loaded from woodchopping.xlsx Results sheet.
        store: Open ResultStore instance.

    Returns:
        Number of new rows inserted (0 on subsequent runs after initial migration).
    """
    if results_df is None or results_df.empty:
        return 0
    return store.import_from_dataframe(results_df, skip_duplicates=True)
