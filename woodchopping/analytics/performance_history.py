"""
Performance History Analysis Module (B2)

Provides historical performance analysis including career summaries, per-event statistics,
recent form tracking, and performance trend analysis.

CRITICAL: Handles missing dates gracefully (only ~55% of results have dates)
"""

from datetime import datetime
from typing import Dict, Optional

import numpy as np
import pandas as pd


def analyze_performance_history(competitor_name: str, df_results: pd.DataFrame) -> Dict:
    """
    Analyze historical performance for a competitor.

    Args:
        competitor_name: Name of the competitor
        df_results: DataFrame with historical results

    Returns:
        Dictionary with comprehensive performance analysis:
        - total_comps: Total number of competitions
        - event_breakdown: Results count per event type (SB/UH)
        - date_range: First/last competition dates (if available)
        - by_event: Per-event statistics (best, avg, std_dev, consistency)
        - recent_form: Last 5 results (if dates available)
        - trend: Performance trend analysis (if enough dated results)
    """

    # Filter results for this competitor
    comp_results = df_results[df_results["Competitor"] == competitor_name].copy()

    if len(comp_results) == 0:
        return {
            "total_comps": 0,
            "event_breakdown": {},
            "date_range": None,
            "by_event": {},
            "recent_form": [],
            "trend": {"direction": "NO DATA", "slope": None},
        }

    # Basic career summary
    total_comps = len(comp_results)
    event_breakdown = comp_results["Event"].value_counts().to_dict()

    # Date range analysis (handle missing dates)
    dated_results = comp_results[comp_results["Date"].notna()].copy()
    if len(dated_results) > 0:
        # Convert dates to datetime if they're strings
        if not pd.api.types.is_datetime64_any_dtype(dated_results["Date"]):
            dated_results["Date"] = pd.to_datetime(dated_results["Date"], errors="coerce")

        dated_results = dated_results[dated_results["Date"].notna()]  # Remove any conversion failures

        if len(dated_results) > 0:
            first_date = dated_results["Date"].min()
            last_date = dated_results["Date"].max()

            # Calculate human-readable time spans
            now = datetime.now()
            if pd.notna(first_date):
                first_comp_ago = _format_time_ago(first_date, now)
            else:
                first_comp_ago = "Unknown"

            if pd.notna(last_date):
                last_comp_ago = _format_time_ago(last_date, now)
            else:
                last_comp_ago = "Unknown"

            date_range = {
                "first": first_date.strftime("%Y-%m-%d") if pd.notna(first_date) else None,
                "last": last_date.strftime("%Y-%m-%d") if pd.notna(last_date) else None,
                "available": len(dated_results),
                "total": total_comps,
                "first_ago": first_comp_ago,
                "last_ago": last_comp_ago,
            }
        else:
            date_range = None
    else:
        date_range = None

    # Per-event statistics
    by_event = {}
    for event in comp_results["Event"].unique():
        event_results = comp_results[comp_results["Event"] == event].copy()

        times = event_results["Time (seconds)"].values
        best_idx = event_results["Time (seconds)"].idxmin()
        best_row = event_results.loc[best_idx]

        # Build best time context string
        best_context_parts = []
        if pd.notna(best_row.get("Size (mm)")):
            best_context_parts.append(f"{int(best_row['Size (mm)'])}mm")
        if pd.notna(best_row.get("Species Code")):
            best_context_parts.append(str(best_row["Species Code"]))
        if pd.notna(best_row.get("Date")):
            date_val = pd.to_datetime(best_row["Date"], errors="coerce")
            if pd.notna(date_val):
                best_context_parts.append(date_val.strftime("%Y-%m-%d"))

        best_context = ", ".join(best_context_parts) if best_context_parts else "No context"

        avg_time = np.mean(times)
        std_dev = np.std(times, ddof=1) if len(times) > 1 else 0.0

        by_event[event] = {
            "best_time": float(best_row["Time (seconds)"]),
            "best_context": best_context,
            "avg_time": float(avg_time),
            "std_dev": float(std_dev),
            "consistency_rating": _get_consistency_rating(std_dev),
            "count": len(event_results),
        }

    # Recent form analysis (only if dates available)
    recent_form = []
    if date_range is not None and len(dated_results) > 0:
        # Sort by date descending and take last 5
        recent = dated_results.sort_values("Date", ascending=False).head(5)

        for _, row in recent.iterrows():
            event = row["Event"]
            time_val = row["Time (seconds)"]

            # Calculate vs average for this event
            if event in by_event:
                vs_average = time_val - by_event[event]["avg_time"]
            else:
                vs_average = 0.0

            # Build context string
            context_parts = []
            if pd.notna(row.get("Size (mm)")):
                context_parts.append(f"{int(row['Size (mm)'])}mm")
            context_parts.append(event)
            context = " ".join(context_parts)

            # Determine note
            note = _get_performance_note(time_val, by_event.get(event, {}).get("best_time"), vs_average)

            recent_form.append(
                {
                    "date": pd.to_datetime(row["Date"]).strftime("%Y-%m-%d"),
                    "time": float(time_val),
                    "context": context,
                    "vs_average": float(vs_average),
                    "note": note,
                }
            )

    # Performance trend analysis (requires minimum 5 dated results)
    trend = (
        _calculate_trend(dated_results)
        if len(dated_results) >= 5
        else {"direction": "INSUFFICIENT DATA (need dates)", "slope": None}
    )

    return {
        "total_comps": total_comps,
        "event_breakdown": event_breakdown,
        "date_range": date_range,
        "by_event": by_event,
        "recent_form": recent_form,
        "trend": trend,
    }


def _get_consistency_rating(std_dev: float) -> str:
    """
    Rate consistency based on standard deviation.

    Thresholds:
    - VERY CONSISTENT: std_dev <= 2.0s
    - CONSISTENT: std_dev <= 3.0s
    - MODERATE: std_dev <= 4.0s
    - VARIABLE: std_dev > 4.0s
    """
    if std_dev <= 2.0:
        return "VERY CONSISTENT"
    elif std_dev <= 3.0:
        return "CONSISTENT"
    elif std_dev <= 4.0:
        return "MODERATE"
    else:
        return "VARIABLE"


def _get_performance_note(time_val: float, best_time: Optional[float], vs_average: float) -> str:
    """
    Generate performance note based on time comparison.

    Args:
        time_val: Actual time
        best_time: Personal best time for this event
        vs_average: Delta from personal average (negative = faster)
    """
    # Check if career best
    if best_time is not None and abs(time_val - best_time) < 0.01:
        return "CAREER BEST"

    # Check vs average
    if vs_average < -1.0:
        return f"ABOVE AVERAGE ({vs_average:.1f}s)"
    elif vs_average > 1.0:
        return f"BELOW AVERAGE (+{vs_average:.1f}s)"
    else:
        return "AVERAGE"


def _format_time_ago(date_val: datetime, now: datetime) -> str:
    """Format time difference in human-readable form."""
    if pd.isna(date_val):
        return "Unknown"

    delta = now - date_val

    if delta.days < 0:
        return "Future date"
    elif delta.days == 0:
        return "Today"
    elif delta.days == 1:
        return "Yesterday"
    elif delta.days < 30:
        return f"{delta.days} days ago"
    elif delta.days < 60:
        return "1 month ago"
    elif delta.days < 365:
        months = delta.days // 30
        return f"{months} months ago"
    else:
        years = delta.days // 365
        if years == 1:
            return "1 year ago"
        else:
            return f"{years} years ago"


def _calculate_trend(dated_results: pd.DataFrame) -> Dict:
    """
    Calculate performance trend using linear regression.

    Args:
        dated_results: DataFrame with dated results (must have 'Date' and 'Time (seconds)' columns)

    Returns:
        Dictionary with:
        - direction: "IMPROVING" / "DECLINING" / "STABLE"
        - slope: Change in seconds per year (negative = improving)
    """
    if len(dated_results) < 5:
        return {"direction": "INSUFFICIENT DATA (need dates)", "slope": None}

    # Convert dates to days since first result
    sorted_results = dated_results.sort_values("Date").copy()
    first_date = sorted_results["Date"].iloc[0]

    sorted_results["days_since_start"] = (sorted_results["Date"] - first_date).dt.days

    # Linear regression: time = slope * days + intercept
    x = sorted_results["days_since_start"].values
    y = sorted_results["Time (seconds)"].values

    # Check if we have variance in x (dates must span more than 1 day)
    if np.std(x) < 1e-6:
        return {"direction": "INSUFFICIENT DATE RANGE", "slope": None}

    # Fit linear regression
    coeffs = np.polyfit(x, y, 1)
    slope_per_day = coeffs[0]

    # Convert to slope per year
    slope_per_year = slope_per_day * 365.25

    # Determine direction (use 0.5 sec/year threshold for "stable")
    if slope_per_year < -0.5:
        direction = "IMPROVING"
    elif slope_per_year > 0.5:
        direction = "DECLINING"
    else:
        direction = "STABLE"

    return {"direction": direction, "slope": float(slope_per_year)}
