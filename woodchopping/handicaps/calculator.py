"""
Handicap mark calculation — STRATHMARK wrapper.

This module is now a thin wrapper around STRATHMARK's HandicapCalculator.
All calculation logic lives in STRATHMARK; improvements there are immediately
available here without any code changes.

The public function signature is unchanged for backward compatibility with
all STRATHEX UI callers.
"""

from typing import Any, Callable, Dict, List, Optional
import pandas as pd

from strathmark import HandicapCalculator, WoodProfile
from woodchopping.strathmark_adapter import (
    build_competitor_records,
    mark_results_to_dicts,
)
from woodchopping.data import standardize_results_data


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
    Calculate handicap marks using STRATHMARK's HandicapCalculator.

    Public signature is identical to the previous implementation.
    Internally delegates all calculation to STRATHMARK.

    Args:
        heat_assignment_df: DataFrame with 'competitor_name' column.
        species: Wood species code.
        diameter: Block diameter in millimetres.
        quality: Wood quality 1-10 (5 = average).
        event_code: 'SB' or 'UH'.
        results_df: Historical results DataFrame.
        progress_callback: Optional callback(current, total, competitor_name).
                           Called after all predictions complete (single batch).
        tournament_results: Optional {name: actual_time} for 97% same-wood weighting.

    Returns:
        List of dicts with keys: name, mark, predicted_time, method_used,
        confidence, explanation, predictions (3-column), performance_std_dev.
        Returns None if no valid predictions generated.
    """
    if quality is None:
        quality = 5
    quality = int(quality)

    # Standardize results for consistent column names and outlier handling
    results_df, _ = standardize_results_data(results_df)

    competitor_names = heat_assignment_df['competitor_name'].tolist()
    if not competitor_names:
        return None

    # Convert STRATHEX data structures to STRATHMARK types
    records = build_competitor_records(
        competitor_names,
        results_df,
        tournament_results=tournament_results,
    )
    wood = WoodProfile(
        species=str(species),
        diameter_mm=float(diameter),
        quality=int(quality),
    )

    # Run STRATHMARK's HandicapCalculator
    calc = HandicapCalculator()
    try:
        mark_results = calc.calculate(
            competitors=records,
            wood=wood,
            event_code=str(event_code).strip().upper(),
            tournament_results=tournament_results or {},
        )
    except (ValueError, RuntimeError):
        return None

    if not mark_results:
        return None

    # Fire progress callback (single-batch — STRATHMARK computes all competitors at once)
    if progress_callback:
        for idx, mr in enumerate(mark_results, 1):
            progress_callback(idx, len(mark_results), mr.name)

    # Convert MarkResult objects back to STRATHEX dict format (preserves 3-column display)
    return mark_results_to_dicts(
        mark_results,
        competitor_records=records,
        wood=wood,
        event_code=str(event_code).strip().upper(),
        results_df=results_df,
    )
