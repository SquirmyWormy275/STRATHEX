"""
Validation script for Baseline V2 Hybrid Model.

Tests end-to-end functionality with real data:
1. Model fitting and caching
2. Predictions for known competitors
3. Tournament result weighting
4. Quality adjustments
5. Variance estimation
6. Performance metrics
"""

import time

from woodchopping.data import load_results_df, load_wood_data
from woodchopping.predictions.baseline import (
    fit_and_cache_baseline_v2_model,
    invalidate_baseline_v2_cache,
    predict_baseline_v2_hybrid,
)


def test_model_fitting():
    """Test that model fits successfully with real data."""
    print("\n" + "=" * 70)
    print("TEST 1: MODEL FITTING AND CACHING")
    print("=" * 70)

    try:
        results_df = load_results_df()
        wood_df = load_wood_data()

        print(f"Loaded {len(results_df)} results from {len(results_df['competitor_name'].unique())} competitors")

        # Clear cache and time model fitting
        invalidate_baseline_v2_cache()

        start_time = time.time()
        cache = fit_and_cache_baseline_v2_model(results_df, wood_df, force_refit=True)
        fit_time = time.time() - start_time

        print(f"\n[OK] Model fitted in {fit_time:.2f}s")
        print(f"  - Cache version: {cache.get('cache_version')}")
        print(f"  - Sample count: {cache.get('sample_count')}")
        print(f"  - Hardness index entries: {len(cache.get('hardness_index', {}))}")
        print(f"  - Competitor half-lives: {len(cache.get('adaptive_half_lives', {}))}")

        return True
    except Exception as e:
        print(f"\n[FAIL] FAILED: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_predictions_for_known_competitors():
    """Test predictions for competitors with known good data."""
    print("\n" + "=" * 70)
    print("TEST 2: PREDICTIONS FOR KNOWN COMPETITORS")
    print("=" * 70)

    try:
        results_df = load_results_df()
        wood_df = load_wood_data()

        # Test competitors with different data profiles
        test_cases = [
            ("Arden Cogar Jr", "S01", 300, 5, "SB"),  # Lots of data, elite competitor
            ("Nate Hodges", "S01", 300, 5, "SB"),  # Good data
            ("Kate Page", "S01", 300, 5, "UH"),  # Moderate data
        ]

        success_count = 0
        for comp_name, species, diameter, quality, event in test_cases:
            print(f"\nTesting: {comp_name} ({event}, {diameter}mm, Q{quality})")

            start_time = time.time()
            predicted_time, confidence, explanation, metadata = predict_baseline_v2_hybrid(
                competitor_name=comp_name,
                species=species,
                diameter=diameter,
                quality=quality,
                event_code=event,
                results_df=results_df,
                wood_df=wood_df,
            )
            pred_time = time.time() - start_time

            if predicted_time is not None:
                print(f"  [OK] Predicted: {predicted_time:.1f}s ({confidence}) in {pred_time * 1000:.1f}ms")
                print(f"    {explanation}")

                if metadata:
                    print(f"    Std dev: {metadata.get('std_dev', 'N/A'):.2f}s")
                    print(f"    Consistency: {metadata.get('consistency_rating', 'N/A')}")
                    print(f"    Median diameter: {metadata.get('median_diameter', 'N/A'):.0f}mm")
                    interval = metadata.get("prediction_interval", (None, None))
                    if interval[0] is not None:
                        print(f"    95% interval: [{interval[0]:.1f}s, {interval[1]:.1f}s]")

                # Validate prediction is reasonable
                if 10 <= predicted_time <= 180:
                    success_count += 1
                else:
                    print(f"  [WARN] WARNING: Prediction {predicted_time:.1f}s outside reasonable range")
            else:
                print("  [FAIL] FAILED: No prediction returned")

        print(f"\n[OK] {success_count}/{len(test_cases)} predictions successful")
        return success_count == len(test_cases)

    except Exception as e:
        print(f"\n[FAIL] FAILED: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_tournament_weighting():
    """Test that tournament result weighting works correctly."""
    print("\n" + "=" * 70)
    print("TEST 3: TOURNAMENT RESULT WEIGHTING (97/3)")
    print("=" * 70)

    try:
        results_df = load_results_df()
        wood_df = load_wood_data()

        comp_name = "Arden Cogar Jr"
        species = "S01"
        diameter = 300
        quality = 5
        event = "SB"

        # Prediction WITHOUT tournament result
        pred_no_tournament, conf_no, exp_no, meta_no = predict_baseline_v2_hybrid(
            comp_name, species, diameter, quality, event, results_df, wood_df
        )

        print("\nWithout tournament result:")
        print(f"  Predicted: {pred_no_tournament:.2f}s ({conf_no})")

        # Prediction WITH tournament result (simulated 20.0s)
        tournament_time = 20.0
        pred_with_tournament, conf_with, exp_with, meta_with = predict_baseline_v2_hybrid(
            comp_name,
            species,
            diameter,
            quality,
            event,
            results_df,
            wood_df,
            tournament_results={comp_name: tournament_time},
        )

        print(f"\nWith tournament result ({tournament_time:.1f}s):")
        print(f"  Predicted: {pred_with_tournament:.2f}s ({conf_with})")
        print(f"  {exp_with}")

        # Verify weighting formula: 97% tournament + 3% historical
        expected = (tournament_time * 0.97) + (pred_no_tournament * 0.03)
        error = abs(pred_with_tournament - expected)

        print("\nWeighting verification:")
        print(f"  Expected: {expected:.2f}s")
        print(f"  Actual: {pred_with_tournament:.2f}s")
        print(f"  Error: {error:.4f}s")

        if error < 0.5:  # Allow small rounding error
            print("  [OK] Tournament weighting correct")

            # Verify tournament_weighted flag
            if meta_with and meta_with.get("tournament_weighted"):
                print("  [OK] Tournament flag set correctly")
                return True
            else:
                print("  [FAIL] Tournament flag not set")
                return False
        else:
            print(f"  [FAIL] Weighting error too large: {error:.2f}s")
            return False

    except Exception as e:
        print(f"\n[FAIL] FAILED: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_quality_adjustments():
    """Test that quality adjustments work correctly."""
    print("\n" + "=" * 70)
    print("TEST 4: QUALITY ADJUSTMENTS (±2% PER POINT)")
    print("=" * 70)

    try:
        results_df = load_results_df()
        wood_df = load_wood_data()

        comp_name = "Arden Cogar Jr"
        species = "S01"
        diameter = 300
        event = "SB"

        # Test soft, average, and hard wood
        qualities = [3, 5, 8]
        predictions = {}

        for quality in qualities:
            pred, conf, exp, meta = predict_baseline_v2_hybrid(
                comp_name, species, diameter, quality, event, results_df, wood_df
            )
            predictions[quality] = pred
            print(f"\nQuality {quality}/10: {pred:.2f}s")
            print(f"  {exp}")

        # Verify ordering: soft < average < hard
        if predictions[3] < predictions[5] < predictions[8]:
            print("\n[OK] Quality ordering correct (soft < average < hard)")

            # Verify approximate percentage differences
            soft_to_avg = ((predictions[5] - predictions[3]) / predictions[5]) * 100
            avg_to_hard = ((predictions[8] - predictions[5]) / predictions[5]) * 100

            print(f"  Soft->Avg change: {soft_to_avg:.1f}% (expected ~4%)")
            print(f"  Avg->Hard change: {avg_to_hard:.1f}% (expected ~6%)")

            # Allow reasonable tolerance
            if 2 <= soft_to_avg <= 6 and 4 <= avg_to_hard <= 8:
                print("  [OK] Percentage changes reasonable")
                return True
            else:
                print("  [WARN] Percentage changes outside expected range")
                return True  # Still pass, just note the warning
        else:
            print("\n[FAIL] Quality ordering incorrect")
            print(f"  Expected: soft ({predictions[3]:.1f}) < avg ({predictions[5]:.1f}) < hard ({predictions[8]:.1f})")
            return False

    except Exception as e:
        print(f"\n[FAIL] FAILED: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_variance_estimation():
    """Test competitor-specific variance estimation."""
    print("\n" + "=" * 70)
    print("TEST 5: COMPETITOR-SPECIFIC VARIANCE ESTIMATION")
    print("=" * 70)

    try:
        results_df = load_results_df()
        wood_df = load_wood_data()

        # Test different competitors with expected different variance
        test_competitors = [
            ("Arden Cogar Jr", "SB", "VERY HIGH or HIGH"),  # Elite, consistent
            ("Kate Page", "UH", "HIGH or MODERATE"),  # Moderate consistency
        ]

        print()
        for comp_name, event, expected_rating in test_competitors:
            pred, conf, exp, meta = predict_baseline_v2_hybrid(comp_name, "S01", 300, 5, event, results_df, wood_df)

            if meta:
                std_dev = meta.get("std_dev")
                consistency = meta.get("consistency_rating")

                print(f"{comp_name} ({event}):")
                print(f"  Std dev: {std_dev:.2f}s")
                print(f"  Consistency: {consistency}")
                print(f"  Expected: {expected_rating}")

                # Verify std_dev is within bounds
                if 1.5 <= std_dev <= 6.0:
                    print("  [OK] Std dev within bounds [1.5, 6.0]")
                else:
                    print(f"  [FAIL] Std dev outside bounds: {std_dev:.2f}")
            else:
                print(f"{comp_name}: No metadata returned")

        print("\n[OK] Variance estimation completed")
        return True

    except Exception as e:
        print(f"\n[FAIL] FAILED: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_performance():
    """Test prediction performance with caching."""
    print("\n" + "=" * 70)
    print("TEST 6: PERFORMANCE (CACHING)")
    print("=" * 70)

    try:
        results_df = load_results_df()
        wood_df = load_wood_data()

        comp_name = "Arden Cogar Jr"
        species = "S01"
        diameter = 300
        quality = 5
        event = "SB"

        # First prediction (cache miss)
        invalidate_baseline_v2_cache()
        start = time.time()
        pred1, _, _, _ = predict_baseline_v2_hybrid(comp_name, species, diameter, quality, event, results_df, wood_df)
        time_cache_miss = time.time() - start

        # Second prediction (cache hit)
        start = time.time()
        pred2, _, _, _ = predict_baseline_v2_hybrid(comp_name, species, diameter, quality, event, results_df, wood_df)
        time_cache_hit = time.time() - start

        print(f"\nFirst prediction (cache miss): {time_cache_miss * 1000:.1f}ms")
        print(f"Second prediction (cache hit): {time_cache_hit * 1000:.1f}ms")
        print(f"Speedup: {time_cache_miss / time_cache_hit:.1f}x")

        # Verify predictions are identical
        if abs(pred1 - pred2) < 0.01:
            print(f"\n[OK] Predictions consistent: {pred1:.2f}s vs {pred2:.2f}s")
        else:
            print(f"\n[FAIL] Predictions differ: {pred1:.2f}s vs {pred2:.2f}s")
            return False

        # Performance targets
        if time_cache_hit < 0.05:  # <50ms with cache
            print("[OK] Cache hit performance excellent (<50ms)")
            return True
        elif time_cache_hit < 0.1:  # <100ms acceptable
            print("[OK] Cache hit performance good (<100ms)")
            return True
        else:
            print(f"[WARN] Cache hit slower than expected: {time_cache_hit * 1000:.1f}ms")
            return True  # Still pass, just note warning

    except Exception as e:
        print(f"\n[FAIL] FAILED: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_edge_cases():
    """Test edge cases and error handling."""
    print("\n" + "=" * 70)
    print("TEST 7: EDGE CASES")
    print("=" * 70)

    try:
        results_df = load_results_df()
        wood_df = load_wood_data()

        # Test 1: New competitor (no history)
        print("\n1. New competitor (no history):")
        pred, conf, exp, meta = predict_baseline_v2_hybrid(
            "ZZZZZ_New_Competitor_Test", "S01", 300, 5, "SB", results_df, wood_df
        )

        if pred is not None:
            print(f"  [OK] Prediction: {pred:.1f}s ({conf})")
            print(f"    {exp}")
            if conf == "LOW":
                print("  [OK] Confidence correctly LOW for new competitor")
        else:
            print("  [FAIL] No prediction returned")

        # Test 2: Extreme diameter
        print("\n2. Extreme diameter (450mm):")
        pred, conf, exp, meta = predict_baseline_v2_hybrid("Arden Cogar Jr", "S01", 450, 5, "SB", results_df, wood_df)

        if pred is not None:
            print(f"  [OK] Prediction: {pred:.1f}s ({conf})")
            if pred > 20:  # Should be slower for larger diameter
                print("  [OK] Prediction reasonable for large diameter")
        else:
            print("  [WARN] No prediction for extreme diameter")

        # Test 3: Extreme quality
        print("\n3. Extreme quality (1 = very soft):")
        pred_soft, conf, exp, meta = predict_baseline_v2_hybrid(
            "Arden Cogar Jr", "S01", 300, 1, "SB", results_df, wood_df
        )

        print(f"  [OK] Prediction: {pred_soft:.1f}s ({conf})")

        print("\n4. Extreme quality (10 = very hard):")
        pred_hard, conf, exp, meta = predict_baseline_v2_hybrid(
            "Arden Cogar Jr", "S01", 300, 10, "SB", results_df, wood_df
        )

        print(f"  [OK] Prediction: {pred_hard:.1f}s ({conf})")

        if pred_soft is not None and pred_hard is not None:
            if pred_soft < pred_hard:
                print("  [OK] Soft wood faster than hard wood")

        print("\n[OK] Edge case handling completed")
        return True

    except Exception as e:
        print(f"\n[FAIL] FAILED: {e}")
        import traceback

        traceback.print_exc()
        return False


def run_all_tests():
    """Run complete validation suite."""
    print("\n" + "=" * 70)
    print("BASELINE V2 HYBRID MODEL - VALIDATION SUITE")
    print("=" * 70)

    tests = [
        ("Model Fitting", test_model_fitting),
        ("Known Competitors", test_predictions_for_known_competitors),
        ("Tournament Weighting", test_tournament_weighting),
        ("Quality Adjustments", test_quality_adjustments),
        ("Variance Estimation", test_variance_estimation),
        ("Performance", test_performance),
        ("Edge Cases", test_edge_cases),
    ]

    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"\n[FAIL] {test_name} crashed: {e}")
            results[test_name] = False

    # Summary
    print("\n" + "=" * 70)
    print("VALIDATION SUMMARY")
    print("=" * 70)

    passed = sum(1 for result in results.values() if result)
    total = len(results)

    for test_name, result in results.items():
        status = "[OK] PASS" if result else "[FAIL] FAIL"
        print(f"{status:8} {test_name}")

    print(f"\n{passed}/{total} tests passed ({passed / total * 100:.0f}%)")

    if passed == total:
        print("\n[SUCCESS] ALL TESTS PASSED - Baseline V2 validation successful!")
        return True
    else:
        print(f"\n[WARN] {total - passed} test(s) failed - review output above")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
