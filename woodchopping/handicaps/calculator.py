# -*- coding: utf-8 -*-
"""
Handicap mark calculation -- STRATHMARK integration wrapper.

The public function signature and STRATHEX dictionary output are retained for
all tournament and UI callers. Prediction methods, method selection, mark
arithmetic, and variance calculation remain owned by STRATHMARK.
"""

import logging
from contextlib import redirect_stdout
from io import StringIO
from typing import Any, Callable, Dict, List, Optional

import pandas as pd

from woodchopping.data import (
    load_competitors_df,
    standardize_results_data,
)
from woodchopping.data.history_merge import merge_result_history
from woodchopping.data.store_registry import get_store
from woodchopping.strathmark_adapter import (
    build_competitor_id_map,
    build_competitor_records,
    build_gender_map,
    build_wood_profile,
    calculate_handicap_results,
    enrich_results_with_roster,
)

_log = logging.getLogger(__name__)


def _load_persistent_history() -> pd.DataFrame:
    """Read accumulated STRATHMARK history without making it a hard dependency."""
    store = get_store()
    if store is None:
        return pd.DataFrame()

    try:
        history = store.get_all_as_dataframe()
    except Exception as exc:
        # Excel is still the judge-canonical source. A derived-store read failure
        # must not prevent a live event from calculating marks.
        _log.warning(
            "Could not read STRATHMARK ResultStore history; using Excel history only: %s",
            exc,
        )
        return pd.DataFrame()

    return history if isinstance(history, pd.DataFrame) else pd.DataFrame()


def calculate_ai_enhanced_handicaps(
    heat_assignment_df: pd.DataFrame,
    species: str,
    diameter: float,
    quality: int,
    event_code: str,
    results_df: pd.DataFrame,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
    tournament_results: Optional[Dict[str, float]] = None,
    prediction_as_of: Any = None,
    include_store_history: bool = True,
) -> Optional[List[Dict[str, Any]]]:
    """
    Calculate handicap marks through the pinned STRATHMARK engine.

    Existing STRATHEX callers and core return fields are retained. The wrapper:
    - combines judge-canonical Excel history with additional ResultStore rows;
    - validates and enriches historical rows with roster metadata;
    - preserves stable competitor identity;
    - fixes one exclusive evidence cutoff for the full field;
    - delegates prediction, uncertainty, and joint mark optimization to
      STRATHMARK v2 through the explicitly selected transport.

    Args:
        heat_assignment_df: DataFrame containing ``competitor_name`` and,
            when available, roster metadata such as ``gender``.
        species: Wood species name or code.
        diameter: Block diameter in millimetres.
        quality: Wood firmness on the existing 1-10 scale (5 = average).
        event_code: ``SB`` or ``UH``.
        results_df: Historical results DataFrame loaded from Excel.
        progress_callback: Optional callback(current, total, competitor_name).
        tournament_results: Retained for caller compatibility. STRATHMARK v2
            reports same-tournament context as ignored and does not reweight it.
        prediction_as_of: Exclusive evidence cutoff persisted with the event.
        include_store_history: Merge the derived ResultStore history. Set false
            when the caller intentionally supplies a curated history window.

    Returns:
        Existing STRATHEX list-of-dicts contract, or ``None`` when calculation
        cannot produce a valid mark sheet.
    """
    if heat_assignment_df is None or heat_assignment_df.empty:
        return None
    if "competitor_name" not in heat_assignment_df.columns:
        return None

    competitor_names = heat_assignment_df["competitor_name"].dropna().astype(str).tolist()
    if not competitor_names:
        return None

    quality = 5 if quality is None else max(1, min(10, int(quality)))
    event_code = str(event_code).strip().upper()

    # Startup migration makes most ResultStore rows duplicates of Excel. Merge
    # with explicit de-duplication so persistent learning adds evidence rather
    # than multiplying it.
    combined_history = (
        merge_result_history(results_df, _load_persistent_history()) if include_store_history else results_df.copy()
    )

    # Apply the existing shared validation/outlier policy before translating
    # historical evidence to STRATHMARK records.
    standardized_results, _ = standardize_results_data(combined_history)
    if standardized_results is None:
        standardized_results = pd.DataFrame()

    # Results carry performance observations; gender lives in the roster.
    # Join the two sources so identity and compatibility metadata are stable.
    # Prefer the full roster, with the selected heat as a safe fallback in
    # slim/test environments.
    roster_messages = StringIO()
    with redirect_stdout(roster_messages):
        roster_df = load_competitors_df()
    if roster_df is None or roster_df.empty or "gender" not in roster_df.columns:
        message = roster_messages.getvalue()
        if message:
            print(message, end="")
        roster_df = heat_assignment_df

    enriched_results = enrich_results_with_roster(
        standardized_results,
        roster_df,
    )
    gender_map = build_gender_map(heat_assignment_df, enriched_results)
    competitor_id_map = build_competitor_id_map(heat_assignment_df, enriched_results)

    records = build_competitor_records(
        competitor_names,
        enriched_results,
        gender_map=gender_map,
        competitor_id_map=competitor_id_map,
    )
    wood = build_wood_profile(species, diameter, quality)

    try:
        handicap_results = calculate_handicap_results(
            competitor_records=records,
            wood=wood,
            event_code=event_code,
            results_df=enriched_results,
            prediction_as_of=prediction_as_of,
        )
    except (ValueError, RuntimeError) as exc:
        print(f"[WARN] STRATHMARK v2 calculation failed: {exc}")
        return None

    if not handicap_results:
        return None

    if progress_callback:
        total = len(handicap_results)
        for index, result in enumerate(handicap_results, 1):
            progress_callback(index, total, result["name"])

    return handicap_results
