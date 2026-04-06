"""Test enhanced feature engineering with 19 features."""

from woodchopping.data import load_results_df, standardize_results_data

# Load results
print("Loading results...")
results_df = load_results_df()
print(f"Loaded {len(results_df)} historical results")
print(f"Columns: {list(results_df.columns)}\n")

# Standardize data first (this normalizes column names)
print("Standardizing data...")
results_df, _ = standardize_results_data(results_df)

# Manually rename columns to expected format (standardize_results_data doesn't fully rename)
column_mapping = {"Time": "raw_time", "Diameter": "size_mm", "Species": "species"}
results_df = results_df.rename(columns=column_mapping)
print(f"After standardization - Columns: {list(results_df.columns)}\n")

# Import after standardization
from woodchopping.data.preprocessing import engineer_features_for_ml

# Engineer features
print("Engineering 19 features...")
features_df = engineer_features_for_ml(results_df)

if features_df is not None:
    print("[OK] Feature engineering successful!")
    print(f"  Total records: {len(features_df)}")
    print(f"  Total columns: {len(features_df.columns)}\n")

    # Check for all 19 expected features
    expected_features = [
        "competitor_avg_time_by_event",  # 1
        "event_encoded",  # 2
        "size_mm",  # 3
        "wood_janka_hardness",  # 4
        "wood_spec_gravity",  # 5
        "competitor_experience",  # 6
        "competitor_trend_slope",  # 7
        "wood_quality",  # 8 - NEW
        "diameter_squared",  # 9 - NEW
        "quality_x_diameter",  # 10 - NEW
        "quality_x_hardness",  # 11 - NEW
        "experience_x_size",  # 12 - NEW
        "competitor_variance",  # 13 - NEW
        "competitor_median_diameter",  # 14 - NEW
        "recency_score",  # 15 - NEW
        "career_phase",  # 16 - NEW
        "seasonal_month_sin",  # 17 - NEW
        "seasonal_month_cos",  # 18 - NEW
        "event_x_diameter",  # 19 - NEW
    ]

    print("Checking for all 19 features:")
    missing_features = []
    for i, feature in enumerate(expected_features, 1):
        if feature in features_df.columns:
            print(f"  [OK] Feature {i:2d}: {feature}")
        else:
            print(f"  [!!] Feature {i:2d}: {feature} - MISSING!")
            missing_features.append(feature)

    if not missing_features:
        print("\n[OK] All 19 features present!")

        # Show sample statistics for new features
        print("\nNew Feature Statistics (Features 8-19):")
        new_features = expected_features[7:]  # Features 8-19
        for feature in new_features:
            if feature in features_df.columns:
                col = features_df[feature]
                print(f"  {feature}:")
                print(f"    Mean: {col.mean():.2f}, Std: {col.std():.2f}, Min: {col.min():.2f}, Max: {col.max():.2f}")
                print(f"    Non-null: {col.notna().sum()}/{len(col)} ({col.notna().sum() / len(col) * 100:.1f}%)")
    else:
        print(f"\n[!!] Missing {len(missing_features)} features: {missing_features}")

    # Check for NaN values in critical features
    print("\nChecking for NaN values in features:")
    has_nans = False
    for feature in expected_features:
        if feature in features_df.columns:
            nan_count = features_df[feature].isna().sum()
            if nan_count > 0:
                print(f"  [!!] {feature}: {nan_count} NaN values ({nan_count / len(features_df) * 100:.1f}%)")
                has_nans = True
    if not has_nans:
        print("  [OK] No NaN values in any feature!")

else:
    print("[!!] Feature engineering failed!")
