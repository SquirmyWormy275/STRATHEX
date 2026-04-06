"""Competitor selection and heat assignment UI functions.

This module handles competitor selection operations including:
- Tournament-wide competitor selection
- Heat assignment for legacy single-heat mode
- Viewing heat assignments
- Removing competitors from heats
"""

from typing import List, Optional, Tuple

import pandas as pd

from woodchopping.data import load_competitors_df, load_results_df
from woodchopping.ui.history_entry import (
    filter_competitors_with_history,
    prompt_add_competitor_times,
)


def select_all_event_competitors(
    comp_df: pd.DataFrame,
    max_competitors: Optional[int] = None,
    results_df: Optional[pd.DataFrame] = None,
    event_code: Optional[str] = None,
    wood_info: Optional[dict] = None,
) -> pd.DataFrame:
    """Select ALL competitors for a tournament event (not just one heat).

    This replaces the old select_competitors_for_heat() function for tournament mode.
    Supports multi-select via comma-separated or range input.

    Args:
        comp_df: Full competitor roster
        max_competitors: Maximum allowed competitors (optional)

    Returns:
        DataFrame: Selected competitors
    """

    if comp_df is None or comp_df.empty:
        print("\nRoster is empty. Please add competitors first.")
        input("Press Enter to continue...")
        return pd.DataFrame()

    if "competitor_name" not in comp_df.columns:
        print("Roster missing 'competitor_name' column.")
        input("Press Enter to continue...")
        return pd.DataFrame()

    # Optional eligibility filtering (requires event_code)
    if event_code:
        if results_df is None:
            results_df = load_results_df()
        eligible_df, blocked = filter_competitors_with_history(comp_df, results_df, event_code)

        # Display blocked competitors (N < 3 results - ABSOLUTE MINIMUM)
        if blocked:
            print(f"\n{'=' * 70}")
            print("  BLOCKED COMPETITORS (Cannot be selected)")
            print(f"{'=' * 70}")
            print(f"{len(blocked)} competitors do not meet ABSOLUTE MINIMUM (3 results):")
            print()
            for name in sorted(blocked):
                print(f"  X {name} - Insufficient {event_code} history")
            print(f"\n{'=' * 70}")

            if wood_info:
                add_now = input("\nAdd historical times now to make them eligible? (y/n): ").strip().lower()
                if add_now == "y":
                    for name in blocked:
                        print(f"\nAdd times for {name} ({event_code})")
                        added = prompt_add_competitor_times(name, event_code, wood_info)
                        if added and results_df is not None:
                            results_df = load_results_df()
                    # Re-filter after adding times
                    eligible_df, blocked = filter_competitors_with_history(comp_df, results_df, event_code)

            if eligible_df.empty:
                print("\nNo eligible competitors after filtering.")
                input("Press Enter to continue...")
                return pd.DataFrame()

        # Display warnings for competitors with low confidence (3 <= N < 10)
        warned_competitors = []
        for idx, row in eligible_df.iterrows():
            if "_warning" in row and row["_warning"]:
                warned_competitors.append((row["competitor_name"], row["_result_count"], row["_warning"]))

        if warned_competitors:
            print(f"\n{'=' * 70}")
            print("  WARNING: Low Confidence Predictions")
            print(f"{'=' * 70}")
            print(f"{len(warned_competitors)} competitors have LESS than recommended minimum (10 results):")
            print()
            for name, count, message in warned_competitors:
                print(f"  ! {name} - Only {count} {event_code} results")
            print("\n  These competitors CAN be selected, but predictions will be")
            print("  less reliable (expect 5-10s error vs typical 2-4s error).")
            print(f"{'=' * 70}")
            input("\nPress Enter to continue...")

        comp_df = eligible_df

    # Display roster with index numbers
    print(f"\n{'=' * 70}")
    print("  SELECT COMPETITORS FOR EVENT")
    print(f"{'=' * 70}")

    if max_competitors:
        print(f"Maximum competitors for this format: {max_competitors}\n")

    print("ROSTER (All Available Competitors):")
    print("-" * 70)
    for idx in range(len(comp_df)):
        row = comp_df.iloc[idx]
        name = row.get("competitor_name", "Unknown")
        country = row.get("competitor_country", "Unknown")

        # Show warning indicator for low confidence competitors
        warning_indicator = ""
        if "_warning" in row and row["_warning"]:
            result_count = row.get("_result_count", "?")
            warning_indicator = f" [WARNING: N={result_count}]"

        print(f"  {idx + 1:3d}) {name:35s} ({country}){warning_indicator}")

    print("\n" + "=" * 70)
    print("INSTRUCTIONS:")
    print("  - Enter single number: 5")
    print("  - Enter multiple numbers (comma-separated): 1,3,5,7")
    print("  - Enter range: 1-10")
    print("  - Combine: 1,3,5-8,12")
    print("  - Press Enter with no input when finished")
    print("=" * 70)

    selected_indices = set()
    total_competitors = len(comp_df)

    while True:
        print(f"\nEligible competitors: {total_competitors}")
        if max_competitors:
            print(f"Selected so far: {len(selected_indices)} / {max_competitors}")
        else:
            print(f"Selected so far: {len(selected_indices)}")
        selection = input("Enter competitor number(s) (or press Enter to finish): ").strip()

        if selection == "":
            break

        # Parse input (supports ranges and comma-separated)
        try:
            for part in selection.split(","):
                part = part.strip()
                if "-" in part:
                    # Range: e.g., "5-10"
                    start, end = part.split("-")
                    start_idx = int(start) - 1
                    end_idx = int(end) - 1
                    for i in range(start_idx, end_idx + 1):
                        if 0 <= i < len(comp_df):
                            selected_indices.add(i)
                        else:
                            print(f"  [WARN] Skipping invalid number: {i + 1}")
                else:
                    # Single number
                    idx = int(part) - 1
                    if 0 <= idx < len(comp_df):
                        selected_indices.add(idx)
                    else:
                        print(f"  [WARN] Invalid number: {part}")

            # Show current selection count
            print(f"  [OK] {len(selected_indices)} competitor(s) selected")

            # Check max limit
            if max_competitors and len(selected_indices) > max_competitors:
                print(f"  [WARN] WARNING: {len(selected_indices)} exceeds maximum of {max_competitors}")
                over = input("    Continue anyway? (y/n): ").strip().lower()
                if over != "y":
                    print("  Resetting selection...")
                    selected_indices = set()

        except ValueError:
            print("  [WARN] Invalid input. Use format: 1,3,5-8,12")

    if not selected_indices:
        print("\nNo competitors selected.")
        return pd.DataFrame()

    # Build DataFrame of selected competitors
    selected_df = comp_df.iloc[sorted(selected_indices)].copy()

    # Display final selection
    print(f"\n{'=' * 70}")
    print(f"  FINAL SELECTION ({len(selected_df)} competitors)")
    print(f"{'=' * 70}")
    for idx, row in enumerate(selected_df.iterrows(), 1):
        _, data = row
        name = data.get("competitor_name", "Unknown")
        country = data.get("competitor_country", "Unknown")
        print(f"  {idx:3d}) {name:35s} ({country})")
    print(f"{'=' * 70}")

    confirm = input("\nConfirm this selection? (y/n): ").strip().lower()
    if confirm != "y":
        print("Selection cancelled. Returning to menu.")
        return pd.DataFrame()

    return selected_df


def competitor_menu(
    comp_df: pd.DataFrame, heat_assignment_df: pd.DataFrame, heat_assignment_names: List[str]
) -> Tuple[pd.DataFrame, pd.DataFrame, List[str]]:
    """Competitor selection menu (legacy single-heat mode).

    Menu options:
    1. Select Competitors for Heat from roster
    2. Add new competitor to roster
    3. View Heat Assignment
    4. Remove competitor from Heat Assignment
    5. Back to Main Menu

    Args:
        comp_df: Full competitor roster
        heat_assignment_df: Currently assigned competitors
        heat_assignment_names: Names of assigned competitors

    Returns:
        tuple: (updated_roster, heat_assignment_df, heat_assignment_names)
    """

    while True:
        print("\n--- Competitor Menu ---")
        print("1) Select Competitors for Heat from roster")
        print("2) Add new competitor to roster")
        print("3) View Heat Assignment")
        print("4) Remove competitor from Heat Assignment")
        print("5) Back to Main Menu")
        s = input("Choose an option: ").strip()

        if s == "1":
            # Reload roster from Excel to ensure we have latest data
            comp_df = load_competitors_df()

            # Select competitors and RETURN TO MAIN MENU
            heat_assignment_df, heat_assignment_names = select_competitors_for_heat(comp_df)
            return comp_df, heat_assignment_df, heat_assignment_names

        elif s == "2":
            # Add new competitor to roster with historical times
            from woodchopping.ui.personnel_ui import add_competitor_with_times

            comp_df = add_competitor_with_times()
            # Stay in competitor menu after adding

        elif s == "3":
            # View current heat assignment
            view_heat_assignment(heat_assignment_df, heat_assignment_names)
            # Stay in competitor menu after viewing

        elif s == "4":
            # Remove from heat assignment (not from roster)
            heat_assignment_df, heat_assignment_names = remove_from_heat(heat_assignment_df, heat_assignment_names)
            # Stay in competitor menu after removing

        elif s == "5" or s == "":
            break
        else:
            print("Invalid selection. Try again.")

    return comp_df, heat_assignment_df, heat_assignment_names


def select_competitors_for_heat(comp_df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    """Select competitors from roster to add to heat assignment (legacy mode).

    This function displays all competitors available in the excel sheet.
    - All competitors have an index number assigned to them for easy selection
    - The Judge enters a competitor's index number to select them for the heat
    - Selected competitors are added to a separate list for the heat
    - Selected competitors' names are displayed after selection is complete
    - The judge presses enter on an empty entry to finalize list

    Args:
        comp_df: Full competitor roster DataFrame

    Returns:
        tuple: (heat_assignment_df, heat_assignment_names)
    """

    if comp_df is None or comp_df.empty:
        print("\nRoster is empty. Please add competitors first.")
        input("Press Enter to continue...")
        return pd.DataFrame(), []

    if "competitor_name" not in comp_df.columns:
        print("Roster missing 'competitor_name' column.")
        input("Press Enter to continue...")
        return pd.DataFrame(), []

    # Display roster with index numbers
    print("\n--- ROSTER (All Available Competitors) ---")
    print("-" * 40)
    for idx in range(len(comp_df)):
        row = comp_df.iloc[idx]
        name = row.get("competitor_name", "Unknown")
        country = row.get("competitor_country", "Unknown")
        print(f"{idx + 1}) {name} ({country})")

    print("\n" + "=" * 40)
    print("INSTRUCTIONS:")
    print("- Enter competitor numbers one at a time")
    print("- Press Enter after each number to add them")
    print("- Press Enter with no input when finished")
    print("=" * 40)

    selected_indices = []
    selected_names = []
    total_competitors = len(comp_df)

    while True:
        print(f"\nEligible competitors: {total_competitors}")
        print(f"Selected so far: {len(selected_names)}")
        selection = input("Enter competitor number (or press Enter to finish): ").strip()

        if selection == "":
            break

        try:
            idx = int(selection) - 1
            if 0 <= idx < len(comp_df):
                if idx not in selected_indices:
                    selected_indices.append(idx)
                    name = comp_df.iloc[idx]["competitor_name"]
                    selected_names.append(name)
                    print(f"[OK] {name} added to heat")
                else:
                    print("Competitor already selected")
            else:
                print("Invalid number. Please try again.")
        except ValueError:
            print("Please enter a valid number")

    if not selected_indices:
        print("\nNo competitors selected.")
        input("Press Enter to return to main menu...")
        return pd.DataFrame(), []

    heat_df = comp_df.iloc[selected_indices].copy()

    print(f"\n[OK] Total {len(selected_names)} competitors added to heat assignment:")
    for name in selected_names:
        print(f"  - {name}")

    input("\nPress Enter to return to main menu...")
    return heat_df, selected_names


def view_heat_assignment(heat_df: pd.DataFrame, heat_names: List[str]) -> None:
    """Display current heat assignment.

    Args:
        heat_df: Heat assignment DataFrame
        heat_names: List of competitor names in heat
    """
    print("\n--- CURRENT HEAT ASSIGNMENT ---")
    print("-" * 40)

    if not heat_names or heat_df.empty:
        print("No competitors currently assigned to heat.")
    else:
        for i, name in enumerate(heat_names, 1):
            country = heat_df[heat_df["competitor_name"] == name]["competitor_country"].values
            country_str = country[0] if len(country) > 0 else "Unknown"
            print(f"{i}) {name} ({country_str})")

        print(f"\nTotal: {len(heat_names)} competitors in heat")

    input("\nPress Enter to continue...")


def remove_from_heat(heat_df: pd.DataFrame, heat_names: List[str]) -> Tuple[pd.DataFrame, List[str]]:
    """Remove competitor from heat assignment (not from roster).

    Args:
        heat_df: Heat assignment DataFrame
        heat_names: List of competitor names in heat

    Returns:
        tuple: (updated_heat_df, updated_heat_names)
    """

    if not heat_names or heat_df.empty:
        print("\nHeat assignment is currently empty.")
        input("Press Enter to continue...")
        return heat_df, heat_names

    print("\n--- REMOVE FROM HEAT ASSIGNMENT ---")
    print("-" * 40)

    for i, name in enumerate(heat_names, 1):
        print(f"{i}) {name}")

    print("\nEnter number to remove or press Enter to cancel:")
    choice = input("Your choice: ").strip()

    if choice == "":
        print("No changes made.")
        input("Press Enter to continue...")
        return heat_df, heat_names

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(heat_names):
            removed_name = heat_names[idx]
            heat_names.remove(removed_name)
            heat_df = heat_df[heat_df["competitor_name"] != removed_name]
            print(f"\n[OK] {removed_name} removed from heat assignment.")
        else:
            print("Invalid selection.")
    except ValueError:
        print("Invalid input.")

    input("Press Enter to continue...")
    return heat_df, heat_names
