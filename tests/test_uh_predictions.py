"""
Test script to diagnose UH prediction issues for 275mm Aspen quality 6
"""

from woodchopping.data.excel_io import load_results_df
from woodchopping.predictions.prediction_aggregator import get_all_predictions

# Configuration
EVENT = "UH"
SPECIES = "Aspen"
DIAMETER = 275
QUALITY = 6

# Competitors mentioned by user
test_competitors = [
    "Erin LaVoie",
    "Cody Labahn",
    "David Moses Jr.",
    "Cole Schlenker",
    "Eric Hoberg",  # Added for comparison
]

print("=" * 80)
print(f"UH PREDICTION ANALYSIS: {DIAMETER}mm {SPECIES}, Quality {QUALITY}")
print("=" * 80)

# Load historical data
results_df = load_results_df()
print(f"\nLoaded {len(results_df)} total historical results")
uh_results = results_df[results_df["event"] == "UH"]
print(f"Found {len(uh_results)} UH results in database\n")

# Analyze each competitor
predictions_data = []

for name in test_competitors:
    print(f"\n{'=' * 60}")
    print(f"Competitor: {name}")
    print("=" * 60)

    # Show raw historical data for this competitor
    comp_uh = uh_results[uh_results["competitor_name"] == name]

    if len(comp_uh) > 0:
        print(f"\nHistorical UH data ({len(comp_uh)} results):")
        for idx, row in comp_uh.iterrows():
            species_name = row.get("species", "Unknown")
            size = row.get("size_mm", "?")
            time = row.get("raw_time", "?")
            date = row.get("date", "No date")
            print(f"  {time}s in {size}mm {species_name} on {date}")
    else:
        print(f"\n*** NO UH HISTORICAL DATA FOR {name} ***")

    # Get predictions
    try:
        predictions = get_all_predictions(name, SPECIES, DIAMETER, QUALITY, EVENT, results_df)

        print("\nPredictions:")
        for pred_type, pred_data in predictions.items():
            pred_time = pred_data.get("time", "N/A")
            confidence = pred_data.get("confidence", "N/A")
            explanation = pred_data.get("explanation", "N/A")
            print(f"  {pred_type}: {pred_time}s (confidence: {confidence})")
            print(f"    > {explanation}")

        # Get the selected prediction (using correct priority: ML > LLM > Baseline)
        if "ml" in predictions and predictions["ml"]["time"] is not None:
            selected_time = predictions["ml"]["time"]
            selected_source = "ML"
            selected_data = predictions["ml"]
        elif "llm" in predictions and predictions["llm"]["time"] is not None:
            selected_time = predictions["llm"]["time"]
            selected_source = "LLM"
            selected_data = predictions["llm"]
        else:
            selected_time = predictions["baseline"]["time"]
            selected_source = "Baseline"
            selected_data = predictions["baseline"]

        predictions_data.append(
            {
                "name": name,
                "predicted_time": selected_time,
                "source": selected_source,
                "has_data": len(comp_uh) > 0,
                "scaled": selected_data.get("scaled", False),
                "original_diameter": selected_data.get("original_diameter"),
                "scaling_warning": selected_data.get("scaling_warning"),
            }
        )

    except Exception as e:
        print(f"\n*** ERROR GETTING PREDICTIONS: {e} ***")
        import traceback

        traceback.print_exc()
        predictions_data.append({"name": name, "predicted_time": None, "source": "ERROR", "has_data": len(comp_uh) > 0})

# Summary table
print("\n\n" + "=" * 80)
print("PREDICTION SUMMARY (with Diameter Scaling)")
print("=" * 80)
print(f"\n{'Competitor':<20} {'Time':<10} {'Mark':<6} {'UH Data':<8} {'Scaling Info'}")
print("-" * 80)

# Sort by predicted time to calculate marks
predictions_data.sort(key=lambda x: x["predicted_time"] if x["predicted_time"] is not None else 999)

slowest_time = max([p["predicted_time"] for p in predictions_data if p["predicted_time"] is not None], default=0)

for pred in predictions_data:
    name = pred["name"]
    time = pred["predicted_time"]
    has_data = "YES" if pred["has_data"] else "NO"

    scaling_info = ""
    if pred.get("scaled") and pred.get("original_diameter"):
        scaling_info = f"Scaled from {pred['original_diameter']:.0f}mm"
    elif not pred["has_data"]:
        scaling_info = "No UH data"

    if time is not None:
        # Calculate mark: slowest gets 3, others get slowest - their_time + 3
        mark = max(3, round(slowest_time - time + 3))
        time_str = f"{time:.1f}s"
        mark_str = f"{mark}"
    else:
        time_str = "N/A"
        mark_str = "N/A"

    print(f"{name:<20} {time_str:<10} {mark_str:<6} {has_data:<8} {scaling_info}")

print("\n" + "=" * 80)
print("ISSUES IDENTIFIED:")
print("=" * 80)

# Identify issues
for pred in predictions_data:
    if not pred["has_data"] and pred["predicted_time"] is not None:
        print(f"WARNING: {pred['name']}: Prediction made WITHOUT any UH historical data")
    elif pred["predicted_time"] is None:
        print(f"WARNING: {pred['name']}: Failed to generate prediction")
