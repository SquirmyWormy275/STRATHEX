"""
Backtesting validation for Baseline V2 Hybrid Model.

Performs leave-one-out cross-validation to measure:
- Mean Absolute Error (MAE) - target <2.5s
- Root Mean Squared Error (RMSE)
- R² score
- Prediction bias (systematic over/under prediction)
- Performance by event type (SB vs UH)
- Performance by skill level (fast vs slow competitors)
"""

import time
from typing import Dict

import numpy as np
import pandas as pd

from woodchopping.data import load_and_clean_results, load_results_df, load_wood_data
from woodchopping.predictions.baseline import (
    invalidate_baseline_v2_cache,
    predict_baseline_v2_hybrid,
)


def perform_leave_one_out_cv(results_df: pd.DataFrame, wood_df: pd.DataFrame, max_samples: int = None) -> pd.DataFrame:
    """
    Perform leave-one-out cross-validation.

    For each result, train on all other results and predict this one.
    Returns DataFrame with actual vs predicted times.
    """
    print("\n" + "=" * 70)
    print("LEAVE-ONE-OUT CROSS-VALIDATION")
    print("=" * 70)

    # Filter to results with valid data
    valid_results = results_df[
        results_df["raw_time"].notna()
        & results_df["species"].notna()
        & results_df["size_mm"].notna()
        & results_df["event"].notna()
    ].copy()

    # Sample if requested (for faster testing)
    if max_samples and len(valid_results) > max_samples:
        print(f"\nSampling {max_samples} results from {len(valid_results)} total...")
        valid_results = valid_results.sample(n=max_samples, random_state=42)

    print(f"\nRunning cross-validation on {len(valid_results)} results...")
    print("This may take several minutes...\n")

    predictions = []
    start_time = time.time()

    for idx, (i, row) in enumerate(valid_results.iterrows()):
        # Show progress every 50 iterations
        if (idx + 1) % 50 == 0:
            elapsed = time.time() - start_time
            rate = (idx + 1) / elapsed
            remaining = (len(valid_results) - idx - 1) / rate
            print(
                f"Progress: {idx + 1}/{len(valid_results)} "
                f"({(idx + 1) / len(valid_results) * 100:.1f}%) - "
                f"ETA: {remaining:.0f}s"
            )

        # Create training set (all except current row)
        train_df = results_df.drop(index=i)

        # Invalidate cache to force retraining
        invalidate_baseline_v2_cache()

        # Get prediction
        try:
            predicted_time, confidence, explanation, metadata = predict_baseline_v2_hybrid(
                competitor_name=row["competitor_name"],
                species=row["species"],
                diameter=row["size_mm"],
                quality=5,  # Default quality (no quality data in historical results)
                event_code=row["event"],
                results_df=train_df,
                wood_df=wood_df,
                tournament_results=None,
                enable_calibration=True,
            )

            if predicted_time is not None:
                predictions.append(
                    {
                        "competitor_name": row["competitor_name"],
                        "event": row["event"],
                        "species": row["species"],
                        "diameter": row["size_mm"],
                        "actual_time": row["raw_time"],
                        "predicted_time": predicted_time,
                        "error": predicted_time - row["raw_time"],
                        "abs_error": abs(predicted_time - row["raw_time"]),
                        "confidence": confidence,
                        "std_dev": metadata.get("std_dev") if metadata else None,
                    }
                )

        except Exception:
            # Skip problematic predictions
            continue

    elapsed = time.time() - start_time
    print(f"\n[OK] Completed {len(predictions)} predictions in {elapsed:.1f}s")
    print(f"Average time per prediction: {elapsed / len(predictions) * 1000:.1f}ms")

    return pd.DataFrame(predictions)


def calculate_metrics(predictions_df: pd.DataFrame) -> Dict:
    """Calculate comprehensive accuracy metrics."""

    mae = predictions_df["abs_error"].mean()
    rmse = np.sqrt((predictions_df["error"] ** 2).mean())

    # R² score
    ss_res = ((predictions_df["actual_time"] - predictions_df["predicted_time"]) ** 2).sum()
    ss_tot = ((predictions_df["actual_time"] - predictions_df["actual_time"].mean()) ** 2).sum()
    r2 = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0

    # Bias (mean error - positive = over-prediction, negative = under-prediction)
    bias = predictions_df["error"].mean()

    # Percentage within thresholds
    within_1s = (predictions_df["abs_error"] <= 1.0).sum() / len(predictions_df) * 100
    within_2s = (predictions_df["abs_error"] <= 2.0).sum() / len(predictions_df) * 100
    within_3s = (predictions_df["abs_error"] <= 3.0).sum() / len(predictions_df) * 100
    within_5s = (predictions_df["abs_error"] <= 5.0).sum() / len(predictions_df) * 100

    return {
        "mae": mae,
        "rmse": rmse,
        "r2": r2,
        "bias": bias,
        "within_1s": within_1s,
        "within_2s": within_2s,
        "within_3s": within_3s,
        "within_5s": within_5s,
        "n_predictions": len(predictions_df),
    }


def analyze_by_event(predictions_df: pd.DataFrame) -> Dict[str, Dict]:
    """Analyze performance by event type (SB vs UH)."""

    results = {}
    for event in predictions_df["event"].unique():
        event_df = predictions_df[predictions_df["event"] == event]
        results[event] = calculate_metrics(event_df)

    return results


def analyze_by_skill_level(predictions_df: pd.DataFrame) -> Dict[str, Dict]:
    """Analyze performance by skill level (fast vs slow competitors)."""

    # Define quartiles based on actual times
    q1 = predictions_df["actual_time"].quantile(0.25)
    q2 = predictions_df["actual_time"].quantile(0.50)
    q3 = predictions_df["actual_time"].quantile(0.75)

    results = {
        "elite": calculate_metrics(predictions_df[predictions_df["actual_time"] <= q1]),
        "advanced": calculate_metrics(
            predictions_df[(predictions_df["actual_time"] > q1) & (predictions_df["actual_time"] <= q2)]
        ),
        "intermediate": calculate_metrics(
            predictions_df[(predictions_df["actual_time"] > q2) & (predictions_df["actual_time"] <= q3)]
        ),
        "novice": calculate_metrics(predictions_df[predictions_df["actual_time"] > q3]),
    }

    return results


def print_metrics_report(metrics: Dict, title: str = "OVERALL METRICS"):
    """Print formatted metrics report."""

    print(f"\n{title}")
    print("-" * 70)
    print(f"Sample size: {metrics['n_predictions']}")
    print("\nAccuracy Metrics:")
    print(f"  MAE (Mean Absolute Error):     {metrics['mae']:.2f}s")
    print(f"  RMSE (Root Mean Squared Error): {metrics['rmse']:.2f}s")
    print(f"  R² Score:                       {metrics['r2']:.3f}")
    print(f"  Bias (mean error):              {metrics['bias']:+.2f}s")

    print("\nPrediction Accuracy Distribution:")
    print(f"  Within ±1s: {metrics['within_1s']:.1f}%")
    print(f"  Within ±2s: {metrics['within_2s']:.1f}%")
    print(f"  Within ±3s: {metrics['within_3s']:.1f}%")
    print(f"  Within ±5s: {metrics['within_5s']:.1f}%")

    # Pass/fail assessment
    print("\nTarget Assessment:")
    if metrics["mae"] < 2.5:
        print(f"  [OK] MAE < 2.5s target MET ({metrics['mae']:.2f}s)")
    else:
        print(f"  [FAIL] MAE < 2.5s target MISSED ({metrics['mae']:.2f}s)")

    if metrics["rmse"] < 4.0:
        print(f"  [OK] RMSE < 4.0s (good) ({metrics['rmse']:.2f}s)")
    elif metrics["rmse"] < 5.0:
        print(f"  [WARN] RMSE 4-5s (acceptable) ({metrics['rmse']:.2f}s)")
    else:
        print(f"  [FAIL] RMSE > 5.0s (poor) ({metrics['rmse']:.2f}s)")

    if abs(metrics["bias"]) < 0.5:
        print(f"  [OK] Low bias ({metrics['bias']:+.2f}s)")
    elif abs(metrics["bias"]) < 1.0:
        print(f"  [WARN] Moderate bias ({metrics['bias']:+.2f}s)")
    else:
        print(f"  [FAIL] High bias ({metrics['bias']:+.2f}s)")


def main():
    """Run comprehensive backtesting validation."""

    print("=" * 70)
    print("BASELINE V2 HYBRID MODEL - BACKTESTING VALIDATION")
    print("=" * 70)

    # Load data
    print("\nLoading data...")
    results_df_raw = load_results_df()
    results_df = load_and_clean_results(results_df_raw)
    wood_df = load_wood_data()
    print(f"Loaded {len(results_df)} results from {results_df['competitor_name'].nunique()} competitors")

    # Perform cross-validation (sample 200 for reasonable runtime)
    # Full dataset would take ~2-3 hours, 200 samples takes ~10-15 minutes
    predictions_df = perform_leave_one_out_cv(results_df, wood_df, max_samples=200)

    if len(predictions_df) == 0:
        print("[FAIL] No predictions generated!")
        return

    # Calculate overall metrics
    print("\n" + "=" * 70)
    print("BACKTESTING RESULTS")
    print("=" * 70)

    overall_metrics = calculate_metrics(predictions_df)
    print_metrics_report(overall_metrics, "OVERALL METRICS")

    # Analyze by event type
    print("\n" + "=" * 70)
    print("PERFORMANCE BY EVENT TYPE")
    print("=" * 70)

    event_metrics = analyze_by_event(predictions_df)
    for event, metrics in event_metrics.items():
        event_name = "Standing Block (SB)" if event == "SB" else "Underhand (UH)"
        print_metrics_report(metrics, f"{event_name}")

    # Analyze by skill level
    print("\n" + "=" * 70)
    print("PERFORMANCE BY SKILL LEVEL")
    print("=" * 70)

    skill_metrics = analyze_by_skill_level(predictions_df)
    for level, metrics in skill_metrics.items():
        print_metrics_report(metrics, f"{level.upper()} COMPETITORS")

    # Final summary
    print("\n" + "=" * 70)
    print("BACKTESTING SUMMARY")
    print("=" * 70)

    if overall_metrics["mae"] < 2.5:
        print("\n[SUCCESS] Baseline V2 achieves target MAE < 2.5s")
        print(f"Actual MAE: {overall_metrics['mae']:.2f}s")
    else:
        print("\n[FAIL] Baseline V2 does not achieve target MAE < 2.5s")
        print(f"Actual MAE: {overall_metrics['mae']:.2f}s")

    # Save detailed results
    output_file = "baseline_v2_backtesting_results.csv"
    predictions_df.to_csv(output_file, index=False)
    print(f"\n[OK] Detailed results saved to {output_file}")


if __name__ == "__main__":
    main()
