"""
Competitor Performance Profiling Module (B4)

Provides detailed competitor strength/weakness analysis including:
- Preferred event, diameter, and species identification
- Diameter and species performance breakdowns with ratings
- Outlier detection for unusually fast/slow performances
"""

from typing import Dict, List, Optional

import numpy as np
import pandas as pd


def profile_competitor_strengths(competitor_name: str, df_results: pd.DataFrame) -> Dict:
    """
    Profile a competitor's strengths and weaknesses across different conditions.

    Args:
        competitor_name: Name of the competitor
        df_results: DataFrame with historical results

    Returns:
        Dictionary with:
        - preferred_event: Event with most results
        - preferred_diameter: Best performing diameter with reasoning
        - preferred_species: Best performing species with reasoning
        - diameter_breakdown: Performance by diameter with ratings
        - species_breakdown: Performance by species with ratings
        - outliers: Unusually fast/slow performances
    """

    # Filter results for this competitor
    comp_results = df_results[df_results["Competitor"] == competitor_name].copy()

    if len(comp_results) == 0:
        return {
            "preferred_event": "NO DATA",
            "preferred_diameter": None,
            "preferred_species": None,
            "diameter_breakdown": {},
            "species_breakdown": {},
            "outliers": {"fast": [], "slow": []},
        }

    # Calculate overall average time (baseline for comparisons)
    overall_avg = comp_results["Time (seconds)"].mean()

    # Preferred event (most results)
    event_counts = comp_results["Event"].value_counts()
    preferred_event = event_counts.index[0] if len(event_counts) > 0 else "NO DATA"

    # Diameter breakdown
    diameter_breakdown = {}
    diameter_stats = []  # For finding preferred diameter

    for diameter in sorted(comp_results["Size (mm)"].dropna().unique()):
        diam_results = comp_results[comp_results["Size (mm)"] == diameter]
        count = len(diam_results)

        if count > 0:
            avg_time = diam_results["Time (seconds)"].mean()
            rating = _get_category_rating(avg_time, overall_avg, count)

            diameter_breakdown[int(diameter)] = {
                "avg_time": float(avg_time),
                "count": count,
                "rating": rating,
            }

            diameter_stats.append({"diameter": int(diameter), "avg_time": avg_time, "count": count})

    # Find preferred diameter (best average among diameters with 3+ results)
    preferred_diameter = _find_preferred_category(diameter_stats, overall_avg, "diameter")

    # Species breakdown
    species_breakdown = {}
    species_stats = []  # For finding preferred species

    for species in comp_results["Species Code"].dropna().unique():
        species_results = comp_results[comp_results["Species Code"] == species]
        count = len(species_results)

        if count > 0:
            avg_time = species_results["Time (seconds)"].mean()
            rating = _get_category_rating(avg_time, overall_avg, count)

            species_breakdown[str(species)] = {
                "avg_time": float(avg_time),
                "count": count,
                "rating": rating,
            }

            species_stats.append({"species": str(species), "avg_time": avg_time, "count": count})

    # Find preferred species (best average among species with 3+ results)
    preferred_species = _find_preferred_category(species_stats, overall_avg, "species")

    # Outlier detection
    outliers = _detect_outliers(comp_results)

    return {
        "preferred_event": preferred_event,
        "preferred_diameter": preferred_diameter,
        "preferred_species": preferred_species,
        "diameter_breakdown": diameter_breakdown,
        "species_breakdown": species_breakdown,
        "outliers": outliers,
    }


def _get_category_rating(category_avg: float, overall_avg: float, count: int) -> str:
    """
    Rate a category (diameter/species) performance relative to overall average.

    Rating thresholds:
    - STRONGEST: >1.0s faster than overall average
    - AVERAGE: within ±1.0s of overall average
    - WEAKER: >1.0s slower than overall average
    - LIMITED DATA: <3 results in category
    - NO DATA: 0 results

    Args:
        category_avg: Average time in this category
        overall_avg: Overall average time across all categories
        count: Number of results in category
    """
    if count == 0:
        return "NO DATA"
    elif count < 3:
        return "LIMITED DATA"

    delta = category_avg - overall_avg

    if delta < -1.0:
        return "STRONGEST"
    elif delta > 1.0:
        return "WEAKER"
    else:
        return "AVERAGE"


def _find_preferred_category(category_stats: List[Dict], overall_avg: float, category_type: str) -> Optional[Dict]:
    """
    Find the preferred category (diameter or species) with best performance.

    Only considers categories with 3+ results.

    Args:
        category_stats: List of dicts with category info
        overall_avg: Overall average time
        category_type: 'diameter' or 'species'

    Returns:
        Dict with category identifier, avg_time, and reason string, or None
    """
    # Filter to categories with sufficient data (3+ results)
    valid_categories = [cat for cat in category_stats if cat["count"] >= 3]

    if not valid_categories:
        return None

    # Find category with best (lowest) average time
    best_category = min(valid_categories, key=lambda x: x["avg_time"])

    category_id = best_category[category_type]
    avg_time = best_category["avg_time"]

    # Build reason string
    reason = f"{avg_time:.1f}s vs {overall_avg:.1f}s overall"

    return {category_type: category_id, "avg_time": float(avg_time), "reason": reason}


def _detect_outliers(comp_results: pd.DataFrame) -> Dict[str, List[Dict]]:
    """
    Detect outlier performances using z-scores.

    Outlier thresholds:
    - Unusually fast: z-score < -1.5
    - Unusually slow: z-score > 1.5

    Args:
        comp_results: DataFrame with competitor's results

    Returns:
        Dict with 'fast' and 'slow' lists of outlier dicts
    """
    if len(comp_results) < 3:
        # Need at least 3 results for meaningful z-scores
        return {"fast": [], "slow": []}

    times = comp_results["Time (seconds)"].values
    mean_time = np.mean(times)
    std_time = np.std(times, ddof=1)

    # Avoid division by zero
    if std_time < 0.01:
        return {"fast": [], "slow": []}

    fast_outliers = []
    slow_outliers = []

    for idx, row in comp_results.iterrows():
        time_val = row["Time (seconds)"]
        z_score = (time_val - mean_time) / std_time

        # Build context string
        context_parts = []
        if pd.notna(row.get("Size (mm)")):
            context_parts.append(f"{int(row['Size (mm)'])}mm")
        if pd.notna(row.get("Event")):
            context_parts.append(str(row["Event"]))
        if pd.notna(row.get("Date")):
            date_val = pd.to_datetime(row["Date"], errors="coerce")
            if pd.notna(date_val):
                context_parts.append(date_val.strftime("%Y-%m-%d"))

        context = ", ".join(context_parts) if context_parts else "No context"

        outlier_data = {"time": float(time_val), "context": context, "z_score": float(abs(z_score))}

        if z_score < -1.5:
            fast_outliers.append(outlier_data)
        elif z_score > 1.5:
            slow_outliers.append(outlier_data)

    # Sort outliers by z-score magnitude (most extreme first)
    fast_outliers.sort(key=lambda x: x["z_score"], reverse=True)
    slow_outliers.sort(key=lambda x: x["z_score"], reverse=True)

    return {"fast": fast_outliers, "slow": slow_outliers}
