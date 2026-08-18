"""
Monte Carlo simulation -- STRATHMARK compatibility wrapper.

The public STRATHEX signatures and result shape are unchanged.  All engine
access is routed through ``woodchopping.strathmark_adapter``.
"""

from typing import Any, Dict, List, Optional

import numpy as np

from config import rules, sim_config
from woodchopping.strathmark_adapter import (
    get_competitor_variance_seconds,
    run_monte_carlo_simulation_engine,
)


def _get_competitor_variance_seconds(comp: Dict[str, Any]) -> float:
    """Return the pinned STRATHMARK per-competitor variance value."""
    return get_competitor_variance_seconds(comp)


def simulate_single_race(
    competitors_with_marks: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Simulate one race and return the existing full finish-detail structure.

    STRATHMARK's single-race helper returns only a winner name; this small local
    compatibility implementation is retained because STRATHEX callers need
    every competitor's actual and elapsed finish time.
    """
    if not competitors_with_marks:
        return []

    finish_results = []
    heat_delta = np.random.normal(0.0, sim_config.HEAT_VARIANCE_SECONDS)

    for competitor in competitors_with_marks:
        predicted_time = competitor.get("predicted_time")
        if predicted_time is None or (isinstance(predicted_time, float) and np.isnan(predicted_time)):
            name = competitor.get("name", "unknown")
            raise ValueError(f"Invalid predicted_time for competitor '{name}': {predicted_time!r}")

        variance_seconds = _get_competitor_variance_seconds(competitor)
        actual_time = np.random.normal(
            predicted_time + heat_delta,
            variance_seconds,
        )
        actual_time = max(actual_time, predicted_time * 0.5)
        start_delay = competitor["mark"] - rules.MIN_MARK_SECONDS
        finish_time = start_delay + actual_time

        finish_results.append(
            {
                "name": competitor["name"],
                "mark": competitor["mark"],
                "actual_time": actual_time,
                "finish_time": finish_time,
                "predicted_time": predicted_time,
            }
        )

    finish_results.sort(key=lambda result: result["finish_time"])
    return finish_results


def run_monte_carlo_simulation(
    competitors_with_marks: List[Dict[str, Any]],
    num_simulations: Optional[int] = None,
    track_finish_orders: bool = False,
    track_podium_margins: bool = False,
    show_live_leaders: bool = False,
    progress_interval: int = 50000,
) -> Dict[str, Any]:
    """
    Run STRATHMARK's Monte Carlo engine and retain STRATHEX's dictionary shape.

    ``CompetitorTimeStats`` objects are converted to the plain dictionaries
    expected by existing reports and UI functions.
    """
    if num_simulations is None:
        num_simulations = sim_config.NUM_SIMULATIONS

    analysis = run_monte_carlo_simulation_engine(
        competitors_with_marks,
        num_simulations=num_simulations,
        track_finish_orders=track_finish_orders,
        track_podium_margins=track_podium_margins,
        show_live_leaders=show_live_leaders,
        progress_interval=progress_interval,
    )

    converted: Dict[str, Any] = {}
    for name, stats in analysis.get("competitor_time_stats", {}).items():
        if hasattr(stats, "mean"):
            converted[name] = {
                "mean": stats.mean,
                "std_dev": stats.std_dev,
                "min": stats.min_time,
                "max": stats.max_time,
                "p25": stats.p25,
                "p50": stats.p50,
                "p75": stats.p75,
                "consistency_rating": stats.consistency_rating,
            }
        else:
            converted[name] = stats

    analysis["competitor_time_stats"] = converted
    return analysis
