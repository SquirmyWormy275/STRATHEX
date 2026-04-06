"""Test script to verify stand/heat generation optimization logic."""

import io
import sys

# Set UTF-8 encoding for console output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from woodchopping.ui.tournament_ui import (
    calculate_tournament_scenarios,
    find_optimal_heat_configuration,
)


def test_stand_optimization():
    """Test the example case: 8 stands, 10 competitors."""

    print("=" * 70)
    print("TESTING STAND/HEAT OPTIMIZATION LOGIC")
    print("=" * 70)
    print()

    # Test Case 1: 8 stands, 10 competitors (user's example)
    print("TEST CASE 1: 8 stands, 10 competitors")
    print("-" * 70)

    scenarios = calculate_tournament_scenarios(num_stands=8, tentative_competitors=10)

    print("\nScenario 0 (Single Heat):")
    print(scenarios["single_heat"]["description"])

    print("\nScenario 1 (Heats -> Finals):")
    print(scenarios["heats_to_finals"]["description"])
    s1 = scenarios["heats_to_finals"]
    print(f"  - Stands per heat: {s1.get('stands_per_heat', 'N/A')}")
    print(f"  - Number of heats: {s1['num_heats']}")
    print(f"  - Max competitors: {s1['max_competitors']}")
    print(f"  - Advancers per heat: {s1['advancers_per_heat']}")

    print("\nScenario 2 (Heats -> Semis -> Finals):")
    print(scenarios["heats_to_semis_to_finals"]["description"])
    s2 = scenarios["heats_to_semis_to_finals"]
    print(f"  - Stands per heat: {s2.get('stands_per_heat', 'N/A')}")
    print(f"  - Number of heats: {s2['num_heats']}")
    print(f"  - Max competitors: {s2['max_competitors']}")
    print(f"  - Advancers per heat: {s2['advancers_per_heat']}")

    # Verify expected behavior for Scenario 1
    print("\n" + "=" * 70)
    print("VERIFICATION FOR SCENARIO 1 (Heats -> Finals)")
    print("=" * 70)
    expected_stands_per_heat = 5
    expected_num_heats = 2
    actual_stands_per_heat = s1.get("stands_per_heat", None)
    actual_num_heats = s1["num_heats"]

    print("Expected: 2 heats of 5 (balanced: 5+5)")
    print(f"Actual:   {actual_num_heats} heats of {actual_stands_per_heat}")

    if actual_stands_per_heat == expected_stands_per_heat and actual_num_heats == expected_num_heats:
        print("[OK] PASS: Correctly optimized to 2 heats of 5!")
    else:
        print("? FAIL: Did not optimize correctly")

    print()
    print("=" * 70)

    # Test Case 2: 6 stands, 10 competitors
    print("\nTEST CASE 2: 6 stands, 10 competitors")
    print("-" * 70)

    scenarios2 = calculate_tournament_scenarios(num_stands=6, tentative_competitors=10)
    s1_2 = scenarios2["heats_to_finals"]

    print("\nScenario 1 (Heats -> Finals):")
    print(scenarios2["heats_to_finals"]["description"])
    print(f"  - Stands per heat: {s1_2.get('stands_per_heat', 'N/A')}")
    print(f"  - Number of heats: {s1_2['num_heats']}")
    print("  - Expected: 2 heats of 5 OR 3 heats of 3-4 (all balanced)")

    print()
    print("=" * 70)

    # Test Case 3: 8 stands, 20 competitors
    print("\nTEST CASE 3: 8 stands, 20 competitors")
    print("-" * 70)

    scenarios3 = calculate_tournament_scenarios(num_stands=8, tentative_competitors=20)
    s1_3 = scenarios3["heats_to_finals"]

    print("\nScenario 1 (Heats -> Finals):")
    print(scenarios3["heats_to_finals"]["description"])
    print(f"  - Stands per heat: {s1_3.get('stands_per_heat', 'N/A')}")
    print(f"  - Number of heats: {s1_3['num_heats']}")
    print("  - Expected: Should create balanced heats (e.g., 4 heats of 5, or 5 heats of 4)")

    print()
    print("=" * 70)

    # Test the optimization function directly
    print("\nDIRECT FUNCTION TEST: find_optimal_heat_configuration()")
    print("-" * 70)

    result = find_optimal_heat_configuration(num_stands=8, tentative_competitors=10, target_advancers=8)

    print("Inputs: 8 stands, 10 competitors, target 8 advancers (for finals)")
    print("Output:")
    print(f"  - stands_per_heat: {result['stands_per_heat']}")
    print(f"  - num_heats: {result['num_heats']}")
    print(f"  - advancers_per_heat: {result['advancers_per_heat']}")
    print(f"  - total_advancers: {result['total_advancers']}")
    print(f"  - imbalance: {result['imbalance']}")
    print(f"  - max_competitors: {result['max_competitors']}")

    print()
    print("=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    test_stand_optimization()
