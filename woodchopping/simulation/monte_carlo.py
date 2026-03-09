"""
Monte Carlo simulation — STRATHMARK wrapper.

This module is now a thin wrapper around STRATHMARK's run_monte_carlo_simulation.
All simulation logic lives in STRATHMARK; improvements there are immediately
available here without any code changes.

The public function signature is unchanged for backward compatibility with
all STRATHEX UI callers. CompetitorTimeStats dataclasses from STRATHMARK are
converted to plain dicts so existing STRATHEX UI code (stats['mean'], etc.)
continues to work without modification.

simulate_single_race() keeps a local implementation because STRATHMARK's version
returns only the winner's name (str), while STRATHEX callers expect the full
list-of-dicts with finish time details.
"""

from typing import List, Dict, Any, Optional

import numpy as np

import strathmark.variance as _sm_variance
from config import rules, sim_config


# ---------------------------------------------------------------------------
# Per-competitor variance (delegates to STRATHMARK's version)
# ---------------------------------------------------------------------------

def _get_competitor_variance_seconds(comp: Dict[str, Any]) -> float:
    """Return per-competitor variance (std-dev) delegating to STRATHMARK."""
    return _sm_variance._get_competitor_variance_seconds(comp)


# ---------------------------------------------------------------------------
# simulate_single_race — kept local for backward compat
# STRATHMARK's version returns str (winner name); STRATHEX expects list[dict].
# ---------------------------------------------------------------------------

def simulate_single_race(competitors_with_marks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Simulate a single race with performance variation.

    Returns the full list-of-dicts sorted by finish time (fastest first).
    Each entry contains: name, mark, actual_time, finish_time, predicted_time.

    Note: STRATHMARK's simulate_single_race() returns only the winner's name.
    This local implementation preserves the STRATHEX return type for callers
    that need the full per-competitor race result breakdown.
    """
    finish_results = []
    heat_delta = np.random.normal(0.0, sim_config.HEAT_VARIANCE_SECONDS)

    for comp in competitors_with_marks:
        variance_seconds = _get_competitor_variance_seconds(comp)
        actual_time = np.random.normal(
            comp['predicted_time'] + heat_delta,
            variance_seconds,
        )
        actual_time = max(actual_time, comp['predicted_time'] * 0.5)
        start_delay = comp['mark'] - rules.MIN_MARK_SECONDS
        finish_time = start_delay + actual_time

        finish_results.append({
            'name': comp['name'],
            'mark': comp['mark'],
            'actual_time': actual_time,
            'finish_time': finish_time,
            'predicted_time': comp['predicted_time'],
        })

    finish_results.sort(key=lambda x: x['finish_time'])
    return finish_results


# ---------------------------------------------------------------------------
# run_monte_carlo_simulation — delegates to STRATHMARK
# ---------------------------------------------------------------------------

def run_monte_carlo_simulation(
    competitors_with_marks: List[Dict[str, Any]],
    num_simulations: Optional[int] = None,
    track_finish_orders: bool = False,
    track_podium_margins: bool = False,
    show_live_leaders: bool = False,
    progress_interval: int = 50000,
) -> Dict[str, Any]:
    """
    Run Monte Carlo simulation to assess handicap fairness.

    Delegates to STRATHMARK's HandicapCalculator.  Public signature is unchanged
    for backward compatibility with all STRATHEX UI callers.

    STRATHMARK returns CompetitorTimeStats dataclasses in competitor_time_stats;
    this wrapper converts them to plain dicts so existing STRATHEX UI code
    (stats['mean'], stats['min'], etc.) continues to work unchanged.

    Args:
        competitors_with_marks: List of dicts with 'name', 'mark', 'predicted_time',
                                 and optionally 'performance_std_dev'.
        num_simulations: Number of races to simulate (defaults to config value).
        track_finish_orders: Track most common finish order.
        track_podium_margins: Track avg podium margins and photo-finish rate.
        show_live_leaders: Print interim leader updates during long runs.
        progress_interval: Simulation count interval for progress updates.

    Returns:
        Analysis dict — same keys as before (see STRATHMARK docs for full list).
    """
    if num_simulations is None:
        num_simulations = sim_config.NUM_SIMULATIONS

    analysis = _sm_variance.run_monte_carlo_simulation(
        competitors_with_marks,
        num_simulations=num_simulations,
        track_finish_orders=track_finish_orders,
        track_podium_margins=track_podium_margins,
        show_live_leaders=show_live_leaders,
        progress_interval=progress_interval,
    )

    # Convert CompetitorTimeStats dataclasses -> plain dicts.
    # STRATHEX UI code reads stats['mean'], stats['min'], stats['max'],
    # but CompetitorTimeStats uses .min_time / .max_time attribute names.
    converted: Dict[str, Any] = {}
    for name, stats in analysis.get('competitor_time_stats', {}).items():
        if hasattr(stats, 'mean'):
            converted[name] = {
                'mean': stats.mean,
                'std_dev': stats.std_dev,
                'min': stats.min_time,
                'max': stats.max_time,
                'p25': stats.p25,
                'p50': stats.p50,
                'p75': stats.p75,
                'consistency_rating': stats.consistency_rating,
            }
        else:
            converted[name] = stats  # already a plain dict

    analysis['competitor_time_stats'] = converted
    return analysis
