# -*- coding: utf-8 -*-
"""
Visualization and display functions for Monte Carlo simulation results.

This module provides text-based visualization of simulation statistics,
including summary reports and bar charts showing win rate distributions.
"""

from typing import Dict, Any


def generate_simulation_summary(analysis: Dict[str, Any]) -> str:
    """
    Generate comprehensive text summary of Monte Carlo simulation results.

    Creates a formatted report showing:
    - Simulation parameters and scope
    - Finish time spread statistics
    - Win probabilities for each competitor
    - Average finish positions
    - Front/back marker performance analysis

    Args:
        analysis: Simulation results dictionary from run_monte_carlo_simulation()
                 containing all statistical metrics

    Returns:
        Formatted multi-line string ready for display

    Report Sections:
        1. Header with simulation count and variance parameters
        2. Finish spread statistics (avg, median, range, tight finish probabilities)
        3. Win probabilities sorted by success rate
        4. Average finish positions sorted by performance
        5. Front/back marker analysis for bias detection

    Example:
        >>> analysis = run_monte_carlo_simulation(competitors)
        >>> summary = generate_simulation_summary(analysis)
        >>> print(summary)
        ======================================================================
        MONTE CARLO SIMULATION RESULTS
        ======================================================================
        Simulated 1,000,000 races with +/- 3s absolute performance variation
        ...
    """
    summary = []
    summary.append("\n" + "="*70)
    summary.append("MONTE CARLO SIMULATION RESULTS")
    summary.append("="*70)
    summary.append(f"Simulated {analysis['num_simulations']} races with +/- 3s absolute performance variation")
    if analysis.get('heat_variance_seconds') is not None:
        summary.append(f"Heat variance: +/-{analysis['heat_variance_seconds']:.1f}s shared effect")
    summary.append("")

    summary.append("FINISH TIME SPREADS:")
    summary.append(f"  Average spread: {analysis['avg_spread']:.1f} seconds")
    summary.append(f"  Median spread:  {analysis['median_spread']:.1f} seconds")
    summary.append(f"  Range: {analysis['min_spread']:.1f}s - {analysis['max_spread']:.1f}s")
    summary.append(f"  Tight finish (<10s): {analysis['tight_finish_prob']*100:.1f}% of races")
    summary.append(f"  Very tight (<5s):    {analysis['very_tight_finish_prob']*100:.1f}% of races")
    summary.append("")

    summary.append("WIN PROBABILITIES:")
    sorted_winners = sorted(analysis['winner_percentages'].items(),
                           key=lambda x: x[1], reverse=True)
    for name, pct in sorted_winners:
        summary.append(f"  {name:25s} {pct:5.1f}% ({analysis['winner_counts'][name]:4d} wins)")
    summary.append("")

    summary.append("AVERAGE FINISH POSITIONS:")
    sorted_positions = sorted(analysis['avg_finish_positions'].items(),
                             key=lambda x: x[1])
    for name, avg_pos in sorted_positions:
        summary.append(f"  {name:25s} Avg position: {avg_pos:.2f}")
    summary.append("")

    summary.append("FRONT/BACK MARKER ANALYSIS:")
    summary.append(f"  Front marker (slowest): {analysis['front_marker_name']}")
    summary.append(f"    Win rate: {analysis['front_marker_wins']/analysis['num_simulations']*100:.1f}%")
    summary.append(f"  Back marker (fastest): {analysis['back_marker_name']}")
    summary.append(f"    Win rate: {analysis['back_marker_wins']/analysis['num_simulations']*100:.1f}%")
    summary.append("="*70)

    return "\n".join(summary)


def visualize_simulation_results(analysis: Dict[str, Any]) -> None:
    """
    Display text-based bar chart of win rate distribution.

    Creates ASCII bar chart showing relative win probabilities for all competitors.
    Bars are scaled relative to the highest win rate to fit terminal width.

    Args:
        analysis: Simulation results dictionary from run_monte_carlo_simulation()

    Display Format:
        - Competitor name (left-aligned, 25 characters)
        - Win percentage (5 characters, 1 decimal)
        - Horizontal bar chart (█ characters, scaled to max 40 chars)

    Bars are sorted by win rate (highest to lowest) to make imbalances visible.

    Example Output:
        ======================================================================
        WIN RATE VISUALIZATION
        ======================================================================
        Alice                    25.3% ████████████████████████████████████████
        Bob                      24.8% ███████████████████████████████████████
        Charlie                  24.9% ███████████████████████████████████████
        David                    25.0% ████████████████████████████████████████
        ======================================================================

    Interpretation:
        - Equal length bars = fair handicaps
        - Longer bars = competitor has advantage
        - Shorter bars = competitor at disadvantage
        - Ideal: all bars within 1-2 characters of each other

    Example:
        >>> analysis = run_monte_carlo_simulation(competitors)
        >>> visualize_simulation_results(analysis)
    """
    print("\n" + "="*70)
    print("WIN RATE VISUALIZATION")
    print("="*70)

    max_pct = max(analysis['winner_percentages'].values())

    sorted_winners = sorted(analysis['winner_percentages'].items(),
                           key=lambda x: x[1], reverse=True)

    for name, pct in sorted_winners:
        bar_length = int((pct / max_pct) * 40)  # Scale to 40 chars max
        bar = "█" * bar_length
        print(f"{name:25s} {pct:5.1f}% {bar}")

    print("="*70)
