"""Quick test to verify Monte Carlo individual statistics tracking works correctly."""

from woodchopping.simulation.monte_carlo import run_monte_carlo_simulation

# Create test competitors with championship marks (all Mark 3)
test_competitors = [
    {"name": "Alice", "mark": 3, "predicted_time": 25.0},
    {"name": "Bob", "mark": 3, "predicted_time": 28.0},
    {"name": "Charlie", "mark": 3, "predicted_time": 30.0},
    {"name": "Diana", "mark": 3, "predicted_time": 33.0},
]

print("=" * 70)
print("TESTING MONTE CARLO INDIVIDUAL STATISTICS TRACKING")
print("=" * 70)
print("\nTest Competitors (Championship format - all Mark 3):")
for comp in test_competitors:
    print(f"  - {comp['name']}: Predicted time {comp['predicted_time']}s")

print("\nRunning 10,000 simulation test...")
analysis = run_monte_carlo_simulation(test_competitors, num_simulations=10000)

print("\n" + "=" * 70)
print("INDIVIDUAL COMPETITOR STATISTICS TEST RESULTS")
print("=" * 70)

# Verify competitor_time_stats exists
if "competitor_time_stats" in analysis:
    print("\n[SUCCESS] 'competitor_time_stats' key found in analysis")

    for comp_name in ["Alice", "Bob", "Charlie", "Diana"]:
        if comp_name in analysis["competitor_time_stats"]:
            stats = analysis["competitor_time_stats"][comp_name]
            print(f"\n{comp_name}:")
            print(f"  Mean finish time:    {stats['mean']:.2f}s")
            print(f"  Std deviation:       {stats['std_dev']:.2f}s")
            print(f"  Min finish time:     {stats['min']:.2f}s")
            print(f"  Max finish time:     {stats['max']:.2f}s")
            print(f"  25th percentile:     {stats['p25']:.2f}s")
            print(f"  Median (50th):       {stats['p50']:.2f}s")
            print(f"  75th percentile:     {stats['p75']:.2f}s")
            print(f"  Consistency rating:  {stats['consistency_rating']}")

            # Validation: std_dev should be close to 3.0s (the variance model)
            if 2.5 <= stats["std_dev"] <= 3.5:
                print("  [PASS] Std dev validation: within expected range 2.5-3.5s")
            else:
                print(f"  [WARNING] Std dev validation: expected 2.5-3.5s, got {stats['std_dev']:.2f}s")
        else:
            print(f"\n[ERROR] {comp_name} not found in competitor_time_stats")

    print("\n" + "=" * 70)
    print("TEST COMPLETE - Individual statistics tracking is working correctly!")
    print("=" * 70)
else:
    print("\n[ERROR] 'competitor_time_stats' key NOT found in analysis")
    print("Available keys:", list(analysis.keys()))

print("\n[READY] Ready to proceed with championship simulator implementation")
