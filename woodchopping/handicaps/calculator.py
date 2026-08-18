# -*- coding: utf-8 -*-
"""
Handicap mark calculation -- STRATHMARK integration wrapper.

The public function signature and STRATHEX dictionary output are retained for
all tournament and UI callers.  Prediction methods, method selection, mark
arithmetic, and variance calculation remain owned by STRATHMARK.
"""

from contextlib import redirect_stdout
from io import StringIO
from typing import Any, Callable, Dict, List, Optional

import pandas as pd

from woodchopping.data import (
    load_competitors_df,
    load_wood_data,
    standardize_results_data,
)
from woodchopping.strathmark_adapter import (
    build_competitor_records,
    build_gender_map,
    build_wood_profile,
    calculate_handicap_results,
    enrich_results_with_roster,
)


def calculate_ai_enhanced_handicaps(
    heat_assignment_df: pd.DataFrame,
    species: str,
    diameter: float,
    quality: int,
    event_code: str,
    results_df: pd.DataFrame,
    progress_callback: Optional[Callable[[int, int, str], None]] = None,
    tournament_results: Optional[Dict[str, float]] = None,
) -> Optional[List[Dict[str, Any]]]:
    """
    Calculate handicap marks through the pinned STRATHMARK engine.

    Existing STRATHEX callers and return fields are unchanged.  The wrapper:
    - validates and enriches historical rows with roster metadata;
    - trains STRATHMARK's ML model from the supplied history;
    - runs Baseline, ML, and LLM predictions once per competitor;
    - selects the lowest-expected-error prediction;
    - delegates mark assignment and variance to STRATHMARK.

    Args:
        heat_assignment_df: DataFrame containing ``competitor_name`` and,
            when available, roster metadata such as ``gender``.
        species: Wood species name or code.
        diameter: Block diameter in millimetres.
        quality: Wood firmness on the existing 1-10 scale (5 = average).
        event_code: ``SB`` or ``UH``.
        results_df: Historical results DataFrame.
        progress_callback: Optional callback(current, total, competitor_name).
        tournament_results: Optional same-tournament actual times.  Existing
            STRATHEX behavior gives these observations 97% weight.

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

    # Apply the existing shared validation/outlier policy before either
    # baseline construction or ML training.
    standardized_results, _ = standardize_results_data(results_df)
    if standardized_results is None:
        standardized_results = pd.DataFrame()

    # Results carry performance observations; gender lives in the roster.
    # Join the two sources so the trained model and live feature vector use the
    # same encoding.  Prefer the full roster, with the selected heat as a safe
    # fallback in slim/test environments.
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

    records = build_competitor_records(
        competitor_names,
        enriched_results,
        tournament_results=tournament_results,
        gender_map=gender_map,
    )
    wood = build_wood_profile(species, diameter, quality)
    wood_df = load_wood_data()

    try:
        handicap_results = calculate_handicap_results(
            competitor_records=records,
            wood=wood,
            event_code=event_code,
            results_df=enriched_results,
            wood_df=wood_df,
            tournament_results=tournament_results,
        )
    except (ValueError, RuntimeError):
        return None

    if not handicap_results:
        return None

    if progress_callback:
        total = len(handicap_results)
        for index, result in enumerate(handicap_results, 1):
            progress_callback(index, total, result["name"])

    return handicap_results
