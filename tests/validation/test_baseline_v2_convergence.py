"""
Convergence Validation for Baseline V2 Hybrid Model.

Tests that the convergence calibration layer successfully minimizes
finish-time spread to <2s in realistic multi-competitor handicap scenarios.

Methodology:
1. Select realistic scenarios (4-10 competitors from actual results)
2. Generate predictions for all competitors
3. Calculate theoretical finish-time spread (predicted times - marks)
4. Verify spread <2s target is achieved
5. Verify ranking preservation (no crossing)
"""

from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from woodchopping.data import load_and_clean_results, load_results_df, load_wood_data
from woodchopping.predictions.baseline import (
    fit_and_cache_baseline_v2_model,
    predict_baseline_v2_hybrid,
)


def generate_handicap_marks(predictions: Dict[str, float]) -> Dict[str, int]:
    """
    Generate handicap marks from predictions using standard AAA rules.

    AAA Rules: Faster choppers need longer delay (higher marks) to give slower
    choppers a fair chance. Fastest gets highest mark (back marker, starts last),
    slowest gets Mark 3 (front marker, starts first).
    """
    # Sort by predicted time (fastest to slowest)
    sorted_preds = sorted(predictions.items(), key=lambda x: x[1], reverse=True)

    # Fastest gets highest mark (back marker)
    fastest_time = sorted_preds[0][1]

    marks = {}
    for name, pred_time in sorted_preds:
        # Mark = 3 + (fastest_time - pred_time), rounded up
        # Faster times get higher marks (longer delay)
        raw_mark = 3 + (fastest_time - pred_time)
        mark = int(np.ceil(raw_mark))
        marks[name] = mark

    return marks


def calculate_finish_time_spread(
    predictions: Dict[str, float], marks: Dict[str, int]
) -> Tuple[float, Dict[str, float]]:
    """
    Calculate theoretical finish-time spread if predictions were exact.

    Returns:
        - spread: max finish time - min finish time (seconds)
        - finish_times: dict of competitor finish times
    """
    finish_times = {}
    for name, pred_time in predictions.items():
        mark = marks[name]
        # Finish time = predicted time - mark (assuming prediction perfect)
        finish_time = pred_time - mark
        finish_times[name] = finish_time

    spread = max(finish_times.values()) - min(finish_times.values())
    return spread, finish_times


def test_convergence_scenario(
    scenario_name: str,
    competitors: List[str],
    event_code: str,
    species: str,
    diameter: float,
    quality: int,
    results_df: pd.DataFrame,
    wood_df: pd.DataFrame,
) -> Dict:
    """Test convergence for a specific scenario."""

    print(f"\n{'=' * 70}")
    print(f"SCENARIO: {scenario_name}")
    print(f"{'=' * 70}")
    print(f"Event: {event_code} | Species: {species} | Diameter: {diameter}mm | Quality: {quality}/10")
    print(f"Competitors: {len(competitors)}")

    # Get predictions for all competitors
    predictions = {}
    predictions_with_calibration = {}
    metadata_list = []

    for comp in competitors:
        # Prediction WITHOUT convergence calibration
        pred_no_cal, conf, exp, meta = predict_baseline_v2_hybrid(
            competitor_name=comp,
            species=species,
            diameter=diameter,
            quality=quality,
            event_code=event_code,
            results_df=results_df,
            wood_df=wood_df,
            tournament_results=None,
            enable_calibration=False,  # Disable convergence
        )

        # Prediction WITH convergence calibration
        pred_with_cal, conf_cal, exp_cal, meta_cal = predict_baseline_v2_hybrid(
            competitor_name=comp,
            species=species,
            diameter=diameter,
            quality=quality,
            event_code=event_code,
            results_df=results_df,
            wood_df=wood_df,
            tournament_results=None,
            enable_calibration=True,  # Enable convergence
        )

        if pred_no_cal and pred_with_cal:
            predictions[comp] = pred_no_cal
            predictions_with_calibration[comp] = pred_with_cal
            metadata_list.append(
                {
                    "name": comp,
                    "pred_no_cal": pred_no_cal,
                    "pred_with_cal": pred_with_cal,
                    "confidence": conf_cal,
                    "std_dev": meta_cal.get("std_dev") if meta_cal else None,
                }
            )

    if len(predictions) < 3:
        print(f"[SKIP] Insufficient predictions ({len(predictions)} < 3)")
        return None

    # Calculate marks and spreads
    marks_no_cal = generate_handicap_marks(predictions)
    marks_with_cal = generate_handicap_marks(predictions_with_calibration)

    spread_no_cal, finish_no_cal = calculate_finish_time_spread(predictions, marks_no_cal)
    spread_with_cal, finish_with_cal = calculate_finish_time_spread(predictions_with_calibration, marks_with_cal)

    # Check ranking preservation
    ranking_no_cal = sorted(predictions.items(), key=lambda x: x[1])
    ranking_with_cal = sorted(predictions_with_calibration.items(), key=lambda x: x[1])
    ranking_preserved = [n for n, _ in ranking_no_cal] == [n for n, _ in ranking_with_cal]

    # Display results
    print("\nPredictions Summary:")
    print(f"{'Competitor':<20} {'No Cal':>8} {'With Cal':>8} {'Mark':>6} {'Finish':>8} {'Std Dev':>8}")
    print("-" * 70)
    for item in metadata_list:
        name = item["name"][:18]
        no_cal = item["pred_no_cal"]
        with_cal = item["pred_with_cal"]
        mark = marks_with_cal.get(item["name"], 0)
        finish = finish_with_cal.get(item["name"], 0)
        std_dev = item["std_dev"] or 0
        print(f"{name:<20} {no_cal:8.2f} {with_cal:8.2f} {mark:6d} {finish:8.2f} {std_dev:8.2f}")

    print("\nConvergence Analysis:")
    print(f"  Without calibration: spread = {spread_no_cal:.2f}s")
    print(f"  With calibration:    spread = {spread_with_cal:.2f}s")
    print(
        f"  Improvement:         {spread_no_cal - spread_with_cal:.2f}s ({(spread_no_cal - spread_with_cal) / spread_no_cal * 100:.1f}%)"
    )
    print(f"  Ranking preserved:   {'YES' if ranking_preserved else 'NO (FAIL)'}")

    # Assessment
    if spread_with_cal < 2.0:
        status = "[OK] PASS"
    elif spread_with_cal < 3.0:
        status = "[WARN] MARGINAL"
    else:
        status = "[FAIL] POOR"

    print("\nTarget Assessment:")
    print(f"  Finish-time spread:  {spread_with_cal:.2f}s (target: <2.0s) {status}")

    return {
        "scenario": scenario_name,
        "n_competitors": len(competitors),
        "spread_no_cal": spread_no_cal,
        "spread_with_cal": spread_with_cal,
        "improvement_pct": (spread_no_cal - spread_with_cal) / spread_no_cal * 100,
        "ranking_preserved": ranking_preserved,
        "pass": spread_with_cal < 2.0,
    }


def main():
    """Run convergence validation tests."""

    print("=" * 70)
    print("BASELINE V2 - CONVERGENCE CALIBRATION VALIDATION")
    print("=" * 70)
    print("\nTests that convergence calibration achieves finish-time spread <2s")
    print("while preserving competitor ranking order.\n")

    # Load data
    print("Loading data...")
    results_df_raw = load_results_df()
    results_df = load_and_clean_results(results_df_raw)
    wood_df = load_wood_data()

    # Prefit model for speed
    print("Fitting model...")
    fit_and_cache_baseline_v2_model(results_df, wood_df, force_refit=True)
    print("[OK] Model cached\n")

    # Define realistic test scenarios
    # Scenarios are constructed from actual competitors who have competed together

    scenarios = []

    # Scenario 1: Elite men's SB (tight competition)
    elite_sb_men = [
        "Arden Cogar Jr",
        "Jason Lentz",
        "Matt Cogar",
        "Nate Hodges",
        "Matt Slingerland",
        "Caleb Rice",
    ]
    scenarios.append(
        {
            "name": "Elite Men SB 300mm",
            "competitors": elite_sb_men,
            "event": "SB",
            "species": "S01",  # White Pine
            "diameter": 300,
            "quality": 5,
        }
    )

    # Scenario 2: Mixed skill SB (wide range)
    mixed_sb = [
        "Arden Cogar Jr",
        "Jason Lentz",
        "Eric Hoberg",
        "Kelly Kerrigan",
        "Cody Labahn",
        "Mason Banks",
        "Jeff Skirvin",
    ]
    scenarios.append(
        {
            "name": "Mixed Skill SB 300mm",
            "competitors": mixed_sb,
            "event": "SB",
            "species": "S01",
            "diameter": 300,
            "quality": 5,
        }
    )

    # Scenario 3: Elite men's UH
    elite_uh_men = [
        "Walt Page",
        "Matt Slingerland",
        "Jason Lentz",
        "Arden Cogar Jr",
        "Ben Knicely",
        "Joey Long",
    ]
    scenarios.append(
        {
            "name": "Elite Men UH 300mm",
            "competitors": elite_uh_men,
            "event": "UH",
            "species": "S01",
            "diameter": 300,
            "quality": 5,
        }
    )

    # Scenario 4: Women's UH (higher variance)
    women_uh = ["Kate Page", "Hanna Quigley", "Lindsay Daun", "Kelly Kerrigan", "Kate Witkowski"]
    scenarios.append(
        {
            "name": "Women UH 300mm",
            "competitors": women_uh,
            "event": "UH",
            "species": "S01",
            "diameter": 300,
            "quality": 5,
        }
    )

    # Scenario 5: Large diameter SB (different wood properties)
    large_diam_sb = [
        "Arden Cogar Jr",
        "Jason Lentz",
        "Matt Cogar",
        "Eric Hoberg",
        "Cody Labahn",
        "Walt Page",
    ]
    scenarios.append(
        {
            "name": "Large Diameter SB 355mm",
            "competitors": large_diam_sb,
            "event": "SB",
            "species": "S06",  # Douglas Fir
            "diameter": 355,
            "quality": 5,
        }
    )

    # Run all scenarios
    results = []
    for scenario in scenarios:
        result = test_convergence_scenario(
            scenario_name=scenario["name"],
            competitors=scenario["competitors"],
            event_code=scenario["event"],
            species=scenario["species"],
            diameter=scenario["diameter"],
            quality=scenario["quality"],
            results_df=results_df,
            wood_df=wood_df,
        )
        if result:
            results.append(result)

    # Summary
    print(f"\n{'=' * 70}")
    print("CONVERGENCE VALIDATION SUMMARY")
    print(f"{'=' * 70}\n")

    print(f"{'Scenario':<30} {'Competitors':>12} {'Spread':>8} {'Status':>10}")
    print("-" * 70)
    for r in results:
        status = "[OK]" if r["pass"] else "[FAIL]"
        print(f"{r['scenario']:<30} {r['n_competitors']:>12} {r['spread_with_cal']:>8.2f}s {status:>10}")

    # Overall stats
    passed = sum(1 for r in results if r["pass"])
    total = len(results)
    avg_spread = np.mean([r["spread_with_cal"] for r in results])
    avg_improvement = np.mean([r["improvement_pct"] for r in results])

    print(f"\n{'=' * 70}")
    print("Overall Statistics:")
    print(f"  Scenarios passing (<2s spread): {passed}/{total} ({passed / total * 100:.0f}%)")
    print(f"  Average spread with calibration: {avg_spread:.2f}s")
    print(f"  Average improvement:             {avg_improvement:.1f}%")

    all_ranking_preserved = all(r["ranking_preserved"] for r in results)
    print(f"  Ranking preserved all scenarios: {'YES' if all_ranking_preserved else 'NO (CRITICAL ISSUE)'}")

    if passed == total:
        print("\n[SUCCESS] All scenarios achieve <2s finish-time spread!")
    elif passed >= total * 0.8:
        print("\n[PARTIAL] Most scenarios pass, some edge cases need refinement")
    else:
        print("\n[FAIL] Convergence calibration needs improvement")


if __name__ == "__main__":
    main()
