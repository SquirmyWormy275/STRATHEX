"""Analyze backtesting outliers to understand prediction errors."""

import pandas as pd

from woodchopping.data import load_and_clean_results, load_results_df

# Load full results
results = load_and_clean_results(load_results_df())

# Load backtesting results
test = pd.read_csv("baseline_v2_realistic_backtesting.csv")

print("=" * 70)
print("OUTLIER ANALYSIS: Cases where prediction error > 20s")
print("=" * 70)
print("\nChecking if actual times are outliers in competitor's history...\n")

outliers = test[test["abs_error"] > 20].copy()

for _, row in outliers.iterrows():
    comp_name = row["competitor_name"]
    actual = row["actual_time"]
    predicted = row["predicted_time"]
    event = row["event"]

    # Get competitor's full history for this event
    comp_history = results[(results["competitor_name"] == comp_name) & (results["event"] == event)]["raw_time"]

    if len(comp_history) > 0:
        median = comp_history.median()
        q25 = comp_history.quantile(0.25)
        q75 = comp_history.quantile(0.75)
        min_time = comp_history.min()
        max_time = comp_history.max()

        # Calculate IQR outlier threshold (Q3 + 1.5*IQR)
        iqr = q75 - q25
        outlier_threshold = q75 + 1.5 * iqr

        is_outlier = actual > outlier_threshold

        print(f"{comp_name} ({event}):")
        print(f"  Actual: {actual:.1f}s | Predicted: {predicted:.1f}s | Error: {row['error']:.1f}s")
        print(f"  History: median={median:.1f}s, Q25={q25:.1f}s, Q75={q75:.1f}s")
        print(f"  Range: {min_time:.1f}s to {max_time:.1f}s (n={len(comp_history)})")
        print(f"  IQR outlier threshold: {outlier_threshold:.1f}s")
        print(f"  Is statistical outlier? {'YES - actual > Q3 + 1.5*IQR' if is_outlier else 'NO'}")
        print()

print("=" * 70)
print("SUMMARY")
print("=" * 70)

total_outliers = len(outliers)
print(f"\nPredictions with error > 20s: {total_outliers}/{len(test)} ({total_outliers / len(test) * 100:.1f}%)")

# Calculate metrics excluding extreme outliers
filtered = test[test["abs_error"] <= 20].copy()
print("\nMetrics EXCLUDING extreme outliers (>20s error):")
print(f"  Sample size: {len(filtered)}")
print(f"  MAE: {filtered['abs_error'].mean():.2f}s")
print(f"  Median error: {filtered['abs_error'].median():.2f}s")
print(f"  MAPE: {filtered['pct_error'].mean():.1f}%")
print(f"  Within +/-3s: {(filtered['abs_error'] <= 3).sum() / len(filtered) * 100:.1f}%")
print(f"  Within +/-5s: {(filtered['abs_error'] <= 5).sum() / len(filtered) * 100:.1f}%")

# Also try excluding 10s outliers
filtered_10 = test[test["abs_error"] <= 10].copy()
print("\nMetrics EXCLUDING major outliers (>10s error):")
print(f"  Sample size: {len(filtered_10)}")
print(f"  MAE: {filtered_10['abs_error'].mean():.2f}s")
print(f"  Median error: {filtered_10['abs_error'].median():.2f}s")
print(f"  MAPE: {filtered_10['pct_error'].mean():.1f}%")
print(f"  Within +/-3s: {(filtered_10['abs_error'] <= 3).sum() / len(filtered_10) * 100:.1f}%")
print(f"  Within +/-5s: {(filtered_10['abs_error'] <= 5).sum() / len(filtered_10) * 100:.1f}%")
