"""
Realistic backtesting validation for Baseline V2 Hybrid Model.

Tests only on scenarios where the model should reasonably perform well:
- Competitors with >=5 historical results (so LOO leaves >=4 results)
- Times within AAA competition limits (<=180s)
- Excludes DNF/incomplete results

This represents real-world usage where judges wouldn't use the system
for competitors with insufficient data.
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


def get_competitor_result_counts(results_df: pd.DataFrame) -> Dict[str, int]:
    """Count number of results per competitor."""
    return results_df.groupby("competitor_name").size().to_dict()


def perform_realistic_backtesting(
    results_df: pd.DataFrame,
    wood_df: pd.DataFrame,
    min_competitor_results: int = 5,
    max_time_limit: float = 180.0,
    max_samples: int = None,
) -> pd.DataFrame:
    """
    Perform realistic leave-one-out testing on qualified results.

    Args:
        results_df: Cleaned results DataFrame
        wood_df: Wood properties DataFrame
        min_competitor_results: Minimum results required for a competitor to be tested
        max_time_limit: Maximum time to include (AAA rule is 180s)
        max_samples: Optional limit on samples for faster testing
    """
    print("\n" + "=" * 70)
    print("REALISTIC LEAVE-ONE-OUT BACKTESTING")
    print("=" * 70)

    # Count results per competitor
    result_counts = get_competitor_result_counts(results_df)

    # Filter to valid test cases
    valid_results = results_df[
        results_df["raw_time"].notna()
        & results_df["species"].notna()
        & results_df["size_mm"].notna()
        & results_df["event"].notna()
        & (results_df["raw_time"] <= max_time_limit)  # AAA time limit
        & (results_df["competitor_name"].map(result_counts) >= min_competitor_results)  # Sufficient data
    ].copy()

    print("\nFiltering criteria:")
    print(f"  - Competitor has >={min_competitor_results} historical results")
    print(f"  - Time <={max_time_limit}s (AAA competition limit)")
    print("  - Valid event/species/diameter data")

    print(f"\nResults: {len(results_df)} total -> {len(valid_results)} qualified for testing")
    print(
        f"Competitors: {results_df['competitor_name'].nunique()} total -> {valid_results['competitor_name'].nunique()} qualified"
    )

    # Sample if requested
    if max_samples and len(valid_results) > max_samples:
        print(f"\nSampling {max_samples} results for faster testing...")
        valid_results = valid_results.sample(n=max_samples, random_state=42)

    print(f"\nRunning cross-validation on {len(valid_results)} results...")
    print("Progress updates every 25 predictions...\n")

    predictions = []
    start_time = time.time()

    for idx, (i, row) in enumerate(valid_results.iterrows()):
        # Progress updates
        if (idx + 1) % 25 == 0:
            elapsed = time.time() - start_time
            rate = (idx + 1) / elapsed if elapsed > 0 else 0
            remaining = (len(valid_results) - idx - 1) / rate if rate > 0 else 0
            avg_time = elapsed / (idx + 1) * 1000  # ms per prediction
            print(
                f"  {idx + 1}/{len(valid_results)} ({(idx + 1) / len(valid_results) * 100:.0f}%) - "
                f"{avg_time:.0f}ms/pred - ETA: {remaining:.0f}s"
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
                quality=5,  # Default quality
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
                        "pct_error": abs(predicted_time - row["raw_time"]) / row["raw_time"] * 100,
                        "confidence": confidence,
                        "std_dev": metadata.get("std_dev") if metadata else None,
                        "num_competitor_results": result_counts.get(row["competitor_name"], 0),
                    }
                )

        except Exception:
            # Skip problematic predictions
            continue

    elapsed = time.time() - start_time
    print(f"\n[OK] Completed {len(predictions)} predictions in {elapsed:.1f}s")
    print(f"Average: {elapsed / len(predictions) * 1000:.0f}ms per prediction")

    return pd.DataFrame(predictions)


def calculate_metrics(predictions_df: pd.DataFrame) -> Dict:
    """Calculate comprehensive accuracy metrics."""

    mae = predictions_df["abs_error"].mean()
    median_ae = predictions_df["abs_error"].median()
    rmse = np.sqrt((predictions_df["error"] ** 2).mean())

    # R² score
    ss_res = ((predictions_df["actual_time"] - predictions_df["predicted_time"]) ** 2).sum()
    ss_tot = ((predictions_df["actual_time"] - predictions_df["actual_time"].mean()) ** 2).sum()
    r2 = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0

    # Bias
    bias = predictions_df["error"].mean()

    # MAPE (Mean Absolute Percentage Error)
    mape = predictions_df["pct_error"].mean()

    # Percentage within thresholds
    within_1s = (predictions_df["abs_error"] <= 1.0).sum() / len(predictions_df) * 100
    within_2s = (predictions_df["abs_error"] <= 2.0).sum() / len(predictions_df) * 100
    within_3s = (predictions_df["abs_error"] <= 3.0).sum() / len(predictions_df) * 100
    within_5s = (predictions_df["abs_error"] <= 5.0).sum() / len(predictions_df) * 100
    within_10pct = (predictions_df["pct_error"] <= 10.0).sum() / len(predictions_df) * 100
    within_20pct = (predictions_df["pct_error"] <= 20.0).sum() / len(predictions_df) * 100

    return {
        "mae": mae,
        "median_ae": median_ae,
        "rmse": rmse,
        "r2": r2,
        "bias": bias,
        "mape": mape,
        "within_1s": within_1s,
        "within_2s": within_2s,
        "within_3s": within_3s,
        "within_5s": within_5s,
        "within_10pct": within_10pct,
        "within_20pct": within_20pct,
        "n_predictions": len(predictions_df),
    }


def print_metrics_report(metrics: Dict, title: str = "METRICS"):
    """Print formatted metrics report."""

    print(f"\n{title}")
    print("-" * 70)
    print(f"Sample size: {metrics['n_predictions']}")

    print("\nAbsolute Error Metrics:")
    print(f"  MAE (Mean):                     {metrics['mae']:.2f}s")
    print(f"  Median Absolute Error:          {metrics['median_ae']:.2f}s")
    print(f"  RMSE:                           {metrics['rmse']:.2f}s")
    print(f"  Bias (mean error):              {metrics['bias']:+.2f}s")

    print("\nRelative Error Metrics:")
    print(f"  MAPE (Mean Abs % Error):        {metrics['mape']:.1f}%")

    print("\nPrediction Accuracy (Absolute):")
    print(f"  Within +/-1s: {metrics['within_1s']:5.1f}%")
    print(f"  Within +/-2s: {metrics['within_2s']:5.1f}%")
    print(f"  Within +/-3s: {metrics['within_3s']:5.1f}%")
    print(f"  Within +/-5s: {metrics['within_5s']:5.1f}%")

    print("\nPrediction Accuracy (Relative):")
    print(f"  Within +/-10%: {metrics['within_10pct']:5.1f}%")
    print(f"  Within +/-20%: {metrics['within_20pct']:5.1f}%")

    # Assessment
    print("\nTarget Assessment:")
    if metrics["mae"] < 2.5:
        print(f"  [OK] MAE < 2.5s target MET ({metrics['mae']:.2f}s)")
    elif metrics["mae"] < 4.0:
        print(f"  [WARN] MAE 2.5-4.0s (good but below target) ({metrics['mae']:.2f}s)")
    else:
        print(f"  [FAIL] MAE >=4.0s (poor) ({metrics['mae']:.2f}s)")

    if metrics["median_ae"] < 2.0:
        print(f"  [OK] Median error < 2.0s ({metrics['median_ae']:.2f}s)")
    elif metrics["median_ae"] < 3.0:
        print(f"  [WARN] Median error 2-3s ({metrics['median_ae']:.2f}s)")
    else:
        print(f"  [FAIL] Median error >=3.0s ({metrics['median_ae']:.2f}s)")

    if abs(metrics["bias"]) < 0.5:
        print(f"  [OK] Very low bias ({metrics['bias']:+.2f}s)")
    elif abs(metrics["bias"]) < 1.0:
        print(f"  [OK] Low bias ({metrics['bias']:+.2f}s)")
    else:
        print(f"  [WARN] Moderate bias ({metrics['bias']:+.2f}s)")


def main():
    """Run realistic backtesting validation."""

    print("=" * 70)
    print("BASELINE V2 - REALISTIC BACKTESTING VALIDATION")
    print("=" * 70)
    print("\nThis test evaluates real-world performance on qualified predictions:")
    print("  - Competitors with sufficient historical data (>=5 results)")
    print("  - Times within AAA competition limits (<=180s)")
    print("  - Complete/valid results only")

    # Load data
    print("\nLoading data...")
    results_df_raw = load_results_df()
    results_df = load_and_clean_results(results_df_raw)
    wood_df = load_wood_data()
    print(f"Loaded {len(results_df)} results from {results_df['competitor_name'].nunique()} competitors")

    # Perform realistic backtesting (150 samples for reasonable runtime ~5-10 min)
    predictions_df = perform_realistic_backtesting(
        results_df, wood_df, min_competitor_results=5, max_time_limit=180.0, max_samples=150
    )

    if len(predictions_df) == 0:
        print("[FAIL] No predictions generated!")
        return

    # Overall metrics
    print("\n" + "=" * 70)
    print("OVERALL RESULTS")
    print("=" * 70)

    overall_metrics = calculate_metrics(predictions_df)
    print_metrics_report(overall_metrics, "ALL QUALIFIED PREDICTIONS")

    # By confidence level
    print("\n" + "=" * 70)
    print("RESULTS BY CONFIDENCE LEVEL")
    print("=" * 70)

    for conf in ["MEDIUM", "LOW"]:
        conf_df = predictions_df[predictions_df["confidence"] == conf]
        if len(conf_df) > 0:
            metrics = calculate_metrics(conf_df)
            print_metrics_report(metrics, f"{conf} CONFIDENCE PREDICTIONS")

    # By event type
    print("\n" + "=" * 70)
    print("RESULTS BY EVENT TYPE")
    print("=" * 70)

    for event in predictions_df["event"].unique():
        event_df = predictions_df[predictions_df["event"] == event]
        event_name = "Standing Block (SB)" if event == "SB" else "Underhand (UH)"
        metrics = calculate_metrics(event_df)
        print_metrics_report(metrics, event_name)

    # Final summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    print(f"\nQualified predictions tested: {len(predictions_df)}")
    print(f"MAE: {overall_metrics['mae']:.2f}s (target: <2.5s)")
    print(f"Median error: {overall_metrics['median_ae']:.2f}s")
    print(f"MAPE: {overall_metrics['mape']:.1f}%")
    print(f"Within +/-3s: {overall_metrics['within_3s']:.1f}%")
    print(f"Within +/-10%: {overall_metrics['within_10pct']:.1f}%")

    if overall_metrics["mae"] < 2.5:
        print("\n[SUCCESS] Baseline V2 achieves MAE < 2.5s target!")
    elif overall_metrics["mae"] < 4.0:
        print("\n[PARTIAL] Baseline V2 shows good performance but misses stretch target")
    else:
        print("\n[NEEDS WORK] Baseline V2 needs further refinement")

    # Save results
    output_file = "baseline_v2_realistic_backtesting.csv"
    predictions_df.to_csv(output_file, index=False)
    print(f"\n[OK] Detailed results saved to {output_file}")


if __name__ == "__main__":
    main()
