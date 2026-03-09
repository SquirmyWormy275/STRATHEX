"""
Handicap fairness assessment — STRATHMARK wrapper.

This module is now a thin wrapper around STRATHMARK's fairness module.
All assessment logic (LLM prompts, statistical fallback, validation)
lives in STRATHMARK; improvements there are immediately available here.

The public function signatures are unchanged for backward compatibility
with all STRATHEX UI callers.
"""

from typing import Dict, Any, List, Optional

from strathmark.fairness import (
    get_ai_assessment_of_handicaps as _sm_assess,
    get_championship_race_analysis as _sm_championship,
    simulate_and_assess_handicaps as _sm_simulate_and_assess,
    format_ai_assessment,
)


def get_ai_assessment_of_handicaps(analysis: Dict[str, Any]) -> str:
    """
    Use LLM to assess fairness of handicap marks from Monte Carlo results.

    Delegates to STRATHMARK's implementation.  Public signature unchanged.

    Args:
        analysis: Simulation results dict from run_monte_carlo_simulation().

    Returns:
        Formatted assessment with FAIRNESS RATING, STATISTICAL ANALYSIS,
        PATTERN DIAGNOSIS, PREDICTION ACCURACY, RECOMMENDATIONS sections.
        Falls back to statistical assessment if Ollama is unavailable.
    """
    return _sm_assess(analysis)


def get_championship_race_analysis(
    analysis: Dict[str, Any],
    predictions: List[Dict],
) -> str:
    """
    Use LLM to generate sports-commentary for a championship race.

    Delegates to STRATHMARK's implementation.  Public signature unchanged.

    Args:
        analysis: Monte Carlo results dict from run_monte_carlo_simulation().
        predictions: List of competitor prediction dicts with 'name',
                     'predicted_time', 'method_used', 'confidence'.

    Returns:
        Formatted race analysis with RACE FAVORITE, KEY MATCHUPS,
        PODIUM BATTLE, DARK HORSE, CONSISTENCY ANALYSIS, RACE DYNAMICS.
    """
    return _sm_championship(analysis, predictions)


def simulate_and_assess_handicaps(
    competitors_with_marks: List[Dict[str, Any]],
    num_simulations: Optional[int] = None,
) -> None:
    """
    Run complete Monte Carlo + display + AI assessment workflow.

    Delegates to STRATHMARK's implementation with show=True so output
    is printed to the console as before.  Return value is None for
    backward compatibility (STRATHMARK returns a dict; callers ignore it).

    Args:
        competitors_with_marks: List of dicts with 'name', 'mark', 'predicted_time'.
        num_simulations: Override for simulation count (defaults to config value).
    """
    _sm_simulate_and_assess(
        competitors_with_marks,
        num_simulations=num_simulations,
        show=True,
    )
