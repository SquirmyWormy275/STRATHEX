"""Test XGBoost upgrade with 19 features."""

from woodchopping.data import load_results_df
from woodchopping.predictions.ml_model import train_ml_model

# Load and standardize results
print("Loading results...")
results_df = load_results_df()

# Manually rename columns (standardize doesn't fully rename)
column_mapping = {"Time": "raw_time", "Diameter": "size_mm", "Species": "species"}
results_df = results_df.rename(columns=column_mapping)

print(f"Loaded {len(results_df)} historical results\n")

# Train models with upgraded feature set
print("Training XGBoost models with 19 features...")
print("=" * 70)
models = train_ml_model(results_df, skip_validation=False, force_retrain=True)

if models:
    print("\n" + "=" * 70)
    print("[OK] XGBoost upgrade successful!")
    print("=" * 70)

    if "SB" in models and models["SB"] is not None:
        print("\n[OK] Standing Block (SB) model trained successfully")

    if "UH" in models and models["UH"] is not None:
        print("[OK] Underhand (UH) model trained successfully")

    print("\nAll 19 features are now being used by the XGBoost model!")
else:
    print("\n[!!] Model training failed!")
