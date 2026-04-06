"""Wood characteristics configuration UI functions.

This module handles wood block configuration menus including:
- Wood species selection
- Block size entry
- Quality rating
- Event code selection (SB/UH)
"""

from typing import Dict

from woodchopping.data import load_wood_data
from woodchopping.data.validation import (
    check_diameter_sample_size,
    get_diameter_variance_warning,
    is_high_variance_diameter,
)


def wood_menu(wood_selection: Dict) -> Dict:
    """Wood characteristics menu for configuring block parameters.

    Args:
        wood_selection: Dictionary containing current wood settings

    Returns:
        dict: Updated wood selection dictionary
    """

    if "event" not in wood_selection:
        wood_selection["event"] = None

    while True:
        print("\n--- Wood Menu ---")

        # Display species name instead of code
        species_code = wood_selection.get("species")
        if species_code:
            from woodchopping.data import get_species_name_from_code

            species_display = get_species_name_from_code(species_code)
        else:
            species_display = None

        print(
            f"Current: species={species_display}, "
            f"size_mm={wood_selection.get('size_mm')}, "
            f"quality={wood_selection.get('quality')}"
        )
        print("1) Select wood species")
        print("2) Enter size (mm)")
        print("3) Enter quality (1 = softest, 4-7 = average for species, 8-10 = hardest)")
        print("4) Back to Main Menu")
        s = input("Choose an option: ").strip()

        if s == "1":
            wood_selection = select_wood_species(wood_selection)

        elif s == "2":
            wood_selection = enter_wood_size_mm(wood_selection)

        elif s == "3":
            wood_selection = enter_wood_quality(wood_selection)

        elif s == "4" or s == "":
            break
        else:
            print("Invalid selection. Try again.")

    return wood_selection


def select_wood_species(wood_selection: Dict) -> Dict:
    """Select wood species from available options.

    Args:
        wood_selection: Current wood selection dictionary

    Returns:
        dict: Updated wood selection with chosen species
    """
    wood_df = load_wood_data()

    if wood_df.empty:
        print("No wood data available.")
        return wood_selection

    # Ensure both species name and code columns exist
    if "species" not in wood_df.columns or "speciesID" not in wood_df.columns:
        print("Wood sheet missing required columns (species or speciesID).")
        return wood_selection

    # Display species with both name and code for clarity
    print("\nAvailable wood species:")
    for i, row in wood_df.iterrows():
        species_name = row["species"]
        species_code = row["speciesID"]
        print(f"{i + 1}) {species_code} - {species_name}")

    choice = input("Select species by number: ").strip()

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(wood_df):
            # CRITICAL: Store species CODE (S01, S02, etc.), NOT name
            wood_selection["species"] = wood_df.iloc[idx]["speciesID"]
            format_wood(wood_selection)
        else:
            print("Invalid selection.")
    except ValueError:
        print("Invalid input.")

    return wood_selection


def enter_wood_size_mm(wood_selection: Dict) -> Dict:
    """Enter block diameter in millimeters.

    Args:
        wood_selection: Current wood selection dictionary

    Returns:
        dict: Updated wood selection with block size
    """
    size = input("Enter block diameter in mm: ").strip()

    try:
        val = float(size)
        wood_selection["size_mm"] = val

        # Check for high-variance diameters
        if is_high_variance_diameter(val):
            print(f"\n{'=' * 70}")
            warning_msg = get_diameter_variance_warning(val)
            if warning_msg:
                print(warning_msg)
            print(f"{'=' * 70}")

            proceed = input("\nProceed with this diameter anyway? (y/n): ").strip().lower()
            if proceed != "y":
                print("Diameter not set. Please select a different size.")
                wood_selection["size_mm"] = None
                return wood_selection

        # Check sample size for this diameter (if event is known)
        event = wood_selection.get("event")
        if event and val:
            from woodchopping.data import load_results_df

            results_df = load_results_df()
            sample_count, confidence = check_diameter_sample_size(results_df, val, event)

            if confidence in ["VERY LOW", "LOW"]:
                print(f"\n{'=' * 70}")
                print("  SPARSE DATA WARNING")
                print(f"{'=' * 70}")
                print(f"Historical data for {int(val)}mm {event}: {sample_count} results")
                print(f"Confidence level: {confidence}")
                print("\nPredictions for this diameter will be based on LIMITED historical data.")
                print("Expect higher uncertainty in handicap calculations.")
                print(f"{'=' * 70}")
                input("\nPress Enter to continue...")

        format_wood(wood_selection)
    except ValueError:
        print("Invalid size input.")

    return wood_selection


def enter_wood_quality(wood_selection: Dict) -> Dict:
    """Enter wood quality rating (1-10 scale).

    Quality scale:
    - 1-3: Soft/rotten wood (faster times)
    - 4-7: Average firmness for species
    - 8-10: Above average firmness (slower times)

    Args:
        wood_selection: Current wood selection dictionary

    Returns:
        dict: Updated wood selection with quality rating
    """
    while True:
        s = input("Enter wood quality (integer 1-10): ").strip()

        if s == "":
            print("No change made to wood quality.")
            break

        try:
            val = int(s)
            val = max(1, min(10, val))  # Clamp between 1 and 10
            wood_selection["quality"] = val
            format_wood(wood_selection)
            break
        except ValueError:
            print("Invalid input. Please enter an integer between 0 and 10.")

    return wood_selection


def format_wood(ws: Dict) -> str:
    """Display formatted header for current wood selection.

    Args:
        ws: Wood selection dictionary

    Returns:
        str: Formatted header string
    """
    species_code = ws.get("species", "--")
    d = ws.get("size_mm", "--")
    q = ws.get("quality", "--")

    # Get species name from code for display
    if species_code != "--":
        from woodchopping.data import get_species_name_from_code

        species_display = get_species_name_from_code(species_code)
    else:
        species_display = "--"

    header = f"Selected Wood -> Species: {species_display}, Diameter: {d} mm, Quality: {q}"
    print(f"Wood selection updated: {header}")
    return header


def select_event_code(wood_selection: Dict) -> Dict:
    """Select event type (Standing Block or Underhand).

    Args:
        wood_selection: Current wood selection dictionary

    Returns:
        dict: Updated wood selection with event code
    """
    while True:
        e = input("Select event: type 'SB' for Standing Block or 'UH' for Underhand: ").strip().upper()

        if e in ("SB", "UH"):
            wood_selection["event"] = e
            print(f"Event selected: {e}")
            return wood_selection

        if e == "":
            print("No change made to event.")
            return wood_selection

        print("Invalid input. Please enter SB or UH.")
