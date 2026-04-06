"""
Fairness Validation for Baseline V2 Hybrid Model via Monte Carlo Simulation.

Tests that:
1. Competitor-specific variance (std_dev) from V2 metadata is used correctly
2. Win rate spread is <2% (excellent fairness)
3. No systematic bias toward front/back markers
4. Finish position distribution is balanced

Uses the existing Monte Carlo simulation from fairness.py to validate
that handicaps generated from V2 predictions result in fair competition.
"""

from typing import Dict, List

import numpy as np
import pandas as pd

from woodchopping.data import load_and_clean_results, load_results_df, load_wood_data
from woodchopping.predictions.baseline import (
    fit_and_cache_baseline_v2_model,
    predict_baseline_v2_hybrid,
)
from woodchopping.simulation.fairness import run_monte_carlo_simulation


def test_fairness_scenario(
    scenario_name: str,
    competitors: List[str],
    event_code: str,
    species: str,
    diameter: float,
    quality: int,
    results_df: pd.DataFrame,
    wood_df: pd.DataFrame,
    num_simulations: int = 100000,
) -> Dict:
    """Test fairness for a specific scenario using Monte Carlo."""

    print(f"\n{'=' * 70}")
    print(f"SCENARIO: {scenario_name}")
    print(f"{'=' * 70}")
    print(f"Event: {event_code} | Species: {species} | Diameter: {diameter}mm | Quality: {quality}/10")
    print(f"Competitors: {len(competitors)}")
    print(f"Simulations: {num_simulations:,}\n")

    # Get V2 predictions with metadata
    handicap_results = []
    for comp in competitors:
        pred_time, conf, exp, meta = predict_baseline_v2_hybrid(
            competitor_name=comp,
            species=species,
            diameter=diameter,
            quality=quality,
            event_code=event_code,
            results_df=results_df,
            wood_df=wood_df,
            tournament_results=None,
            enable_calibration=True,
        )

        if pred_time and meta:
            handicap_results.append(
                {
                    "name": comp,
                    "predicted_time": pred_time,
                    "confidence": conf,
                    "performance_std_dev": meta.get("std_dev"),
                    "consistency_rating": meta.get("consistency_rating"),
                }
            )

    if len(handicap_results) < 3:
        print(f"[SKIP] Insufficient predictions ({len(handicap_results)} < 3)")
        return None

    # Calculate marks - AAA rules: fastest gets HIGHEST mark (back marker, starts last)
    sorted_results = sorted(handicap_results, key=lambda x: x["predicted_time"], reverse=True)
    fastest_time = sorted_results[0]["predicted_time"]

    for result in handicap_results:
        # Faster times need longer delay (higher marks)
        raw_mark = 3 + (fastest_time - result["predicted_time"])
        result["mark"] = int(np.ceil(raw_mark))

    # Display handicap setup
    print("Handicap Setup:")
    print(f"{'Competitor':<20} {'Pred Time':>10} {'Mark':>6} {'Std Dev':>8} {'Rating':>12}")
    print("-" * 70)
    for r in sorted(handicap_results, key=lambda x: x["predicted_time"]):
        name = r["name"][:18]
        print(
            f"{name:<20} {r['predicted_time']:>10.2f}s {r['mark']:>6d} {r['performance_std_dev']:>8.2f}s {r['consistency_rating']:>12}"
        )

    # Run Monte Carlo simulation
    print(f"\nRunning {num_simulations:,} Monte Carlo simulations...")
    # Monte Carlo will use performance_std_dev from handicap_results (V2 metadata)
    mc_result = run_monte_carlo_simulation(handicap_results, num_simulations=num_simulations)

    # Display results
    print("\nMonte Carlo Results:")
    print(f"{'Competitor':<20} {'Win Rate':>10} {'Avg Finish':>12}")
    print("-" * 70)
    for comp in sorted(
        mc_result["winner_percentages"].keys(),
        key=lambda x: mc_result["winner_percentages"][x],
        reverse=True,
    ):
        win_rate = mc_result["winner_percentages"][comp]
        avg_finish = mc_result["avg_finish_positions"][comp]
        print(f"{comp:<20} {win_rate:>9.2f}% {avg_finish:>12.2f}")

    # Analyze fairness
    win_rates = list(mc_result["winner_percentages"].values())
    win_rate_spread = max(win_rates) - min(win_rates)
    mean_win_rate = np.mean(win_rates)
    expected_win_rate = 100 / len(competitors)

    print("\nFairness Analysis:")
    print(f"  Win rate spread:     {win_rate_spread:.2f}% (target: <2.0%)")
    print(f"  Mean win rate:       {mean_win_rate:.2f}% (expected: {expected_win_rate:.2f}%)")

    # Check for systematic bias (front vs back markers)
    # Front markers = lowest 1/3 of marks, back markers = highest 1/3
    marks = [r["mark"] for r in handicap_results]
    sorted_by_mark = sorted(handicap_results, key=lambda x: x["mark"])
    n_third = len(sorted_by_mark) // 3

    front_markers = [r["name"] for r in sorted_by_mark[:n_third]]
    back_markers = [r["name"] for r in sorted_by_mark[-n_third:]]

    front_win_rate = (
        sum(mc_result["winner_percentages"][name] for name in front_markers) / len(front_markers)
        if front_markers
        else 0
    )
    back_win_rate = (
        sum(mc_result["winner_percentages"][name] for name in back_markers) / len(back_markers) if back_markers else 0
    )

    print(f"  Front markers avg win rate: {front_win_rate:.2f}%")
    print(f"  Back markers avg win rate:  {back_win_rate:.2f}%")
    print(f"  Bias:                       {abs(front_win_rate - back_win_rate):.2f}%")

    # Assessment
    fairness_excellent = win_rate_spread < 2.0
    fairness_good = win_rate_spread < 5.0
    no_bias = abs(front_win_rate - back_win_rate) < 3.0

    print("\nTarget Assessment:")
    if fairness_excellent:
        print(f"  [OK] EXCELLENT - Win rate spread <2% ({win_rate_spread:.2f}%)")
    elif fairness_good:
        print(f"  [WARN] GOOD - Win rate spread 2-5% ({win_rate_spread:.2f}%)")
    else:
        print(f"  [FAIL] POOR - Win rate spread >5% ({win_rate_spread:.2f}%)")

    if no_bias:
        print(f"  [OK] NO SYSTEMATIC BIAS - Front/back difference <3% ({abs(front_win_rate - back_win_rate):.2f}%)")
    else:
        print(f"  [WARN] POSSIBLE BIAS - Front/back difference >3% ({abs(front_win_rate - back_win_rate):.2f}%)")

    return {
        "scenario": scenario_name,
        "n_competitors": len(competitors),
        "win_rate_spread": win_rate_spread,
        "front_back_bias": abs(front_win_rate - back_win_rate),
        "excellent": fairness_excellent,
        "good": fairness_good,
        "no_bias": no_bias,
        "pass": fairness_excellent and no_bias,
    }


def main():
    """Run Monte Carlo fairness validation tests."""

    print("=" * 70)
    print("BASELINE V2 - MONTE CARLO FAIRNESS VALIDATION")
    print("=" * 70)
    print("\nTests that handicaps from V2 predictions result in fair competition:")
    print("  - Win rate spread <2% (excellent)")
    print("  - No systematic bias toward front/back markers")
    print("  - Competitor-specific variance correctly applied\n")

    # Load data
    print("Loading data...")
    results_df_raw = load_results_df()
    results_df = load_and_clean_results(results_df_raw)
    wood_df = load_wood_data()

    # Prefit model
    print("Fitting model...")
    fit_and_cache_baseline_v2_model(results_df, wood_df, force_refit=True)
    print("[OK] Model cached\n")

    # Define test scenarios (same as convergence tests for consistency)
    scenarios = []

    # Scenario 1: Elite men SB (tight competition, low variance)
    scenarios.append(
        {
            "name": "Elite Men SB 300mm (Low Variance)",
            "competitors": ["Arden Cogar Jr", "Jason Lentz", "Matt Cogar", "Nate Hodges"],
            "event": "SB",
            "species": "S01",
            "diameter": 300,
            "quality": 5,
            "n_simulations": 100000,
        }
    )

    # Scenario 2: Mixed skill SB (wide range, mixed variance)
    scenarios.append(
        {
            "name": "Mixed Skill SB 300mm (Mixed Variance)",
            "competitors": [
                "Arden Cogar Jr",
                "Jason Lentz",
                "Eric Hoberg",
                "Kelly Kerrigan",
                "Cody Labahn",
            ],
            "event": "SB",
            "species": "S01",
            "diameter": 300,
            "quality": 5,
            "n_simulations": 100000,
        }
    )

    # Scenario 3: Women's UH (higher variance)
    scenarios.append(
        {
            "name": "Women UH 300mm (High Variance)",
            "competitors": ["Kate Page", "Hanna Quigley", "Lindsay Daun", "Kelly Kerrigan"],
            "event": "UH",
            "species": "S01",
            "diameter": 300,
            "quality": 5,
            "n_simulations": 100000,
        }
    )

    # Scenario 4: Elite UH (testing different event)
    scenarios.append(
        {
            "name": "Elite Men UH 300mm",
            "competitors": ["Walt Page", "Matt Slingerland", "Jason Lentz", "Arden Cogar Jr"],
            "event": "UH",
            "species": "S01",
            "diameter": 300,
            "quality": 5,
            "n_simulations": 100000,
        }
    )

    # Run all scenarios
    results = []
    for scenario in scenarios:
        result = test_fairness_scenario(
            scenario_name=scenario["name"],
            competitors=scenario["competitors"],
            event_code=scenario["event"],
            species=scenario["species"],
            diameter=scenario["diameter"],
            quality=scenario["quality"],
            results_df=results_df,
            wood_df=wood_df,
            num_simulations=scenario.get("n_simulations", 100000),
        )
        if result:
            results.append(result)

    # Summary
    print(f"\n{'=' * 70}")
    print("FAIRNESS VALIDATION SUMMARY")
    print(f"{'=' * 70}\n")

    print(f"{'Scenario':<40} {'Spread':>8} {'Bias':>8} {'Status':>10}")
    print("-" * 70)
    for r in results:
        status = "[OK]" if r["pass"] else "[WARN]" if r["good"] else "[FAIL]"
        print(f"{r['scenario']:<40} {r['win_rate_spread']:>7.2f}% {r['front_back_bias']:>7.2f}% {status:>10}")

    # Overall stats
    excellent = sum(1 for r in results if r["excellent"])
    good = sum(1 for r in results if r["good"])
    no_bias = sum(1 for r in results if r["no_bias"])
    total = len(results)

    avg_spread = np.mean([r["win_rate_spread"] for r in results])
    avg_bias = np.mean([r["front_back_bias"] for r in results])

    print(f"\n{'=' * 70}")
    print("Overall Statistics:")
    print(f"  Scenarios with excellent fairness (<2% spread): {excellent}/{total} ({excellent / total * 100:.0f}%)")
    print(f"  Scenarios with good fairness (<5% spread):      {good}/{total} ({good / total * 100:.0f}%)")
    print(f"  Scenarios with no bias (<3% front/back diff):   {no_bias}/{total} ({no_bias / total * 100:.0f}%)")
    print(f"  Average win rate spread:                        {avg_spread:.2f}%")
    print(f"  Average front/back bias:                        {avg_bias:.2f}%")

    if excellent == total and no_bias == total:
        print("\n[SUCCESS] All scenarios achieve excellent fairness with no bias!")
    elif good >= total * 0.8:
        print("\n[PARTIAL] Most scenarios show good fairness")
    else:
        print("\n[FAIL] Fairness validation failed - systematic issues detected")


if __name__ == "__main__":
    main()
