"""Monte Carlo simulation for handicap fairness assessment."""

from woodchopping.simulation.fairness import (
    get_ai_assessment_of_handicaps,
    get_championship_race_analysis,
    simulate_and_assess_handicaps,
)
from woodchopping.simulation.monte_carlo import run_monte_carlo_simulation, simulate_single_race
from woodchopping.simulation.visualization import (
    generate_simulation_summary,
    visualize_simulation_results,
)

__all__ = [
    "simulate_single_race",
    "run_monte_carlo_simulation",
    "generate_simulation_summary",
    "visualize_simulation_results",
    "get_ai_assessment_of_handicaps",
    "simulate_and_assess_handicaps",
    "get_championship_race_analysis",
]
