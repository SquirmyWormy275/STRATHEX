# -*- coding: utf-8 -*-
"""
STRATHEX - Woodchopping Handicap Calculator v5.2
Professional Competition System
"""

#Import Pandas, numpy,
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import sys
from math import ceil
from openpyxl import load_workbook
import time
import os
from datetime import datetime

# Fix Windows console encoding for Unicode characters
if sys.platform == 'win32':
    try:
        import subprocess
        subprocess.run(['chcp', '65001'], capture_output=True, shell=True)
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass  # If it fails, we'll fallback to ASCII banner

# Import functions from modular woodchopping package
from woodchopping.data import (
    load_competitors_df,
    load_results_df,
    append_results_to_excel,
)
from woodchopping.ui import (
    wood_menu,
    select_event_code,
    select_all_event_competitors,
    personnel_management_menu,
    run_championship_simulator,
    display_and_export_schedule,
)
from woodchopping.ui.handicap_ui import (
    judge_approval,
    
    manual_adjust_handicaps,
)
from woodchopping.ui.adjustment_tracking import (
    log_handicap_adjustment,
    view_adjustment_history,
)
from woodchopping.analytics.prediction_accuracy import (
    analyze_prediction_accuracy,
    format_prediction_accuracy_report,
)
from woodchopping.predictions.prediction_aggregator import (
    display_basic_prediction_table,
    display_comprehensive_prediction_analysis,
    display_handicap_calculation_explanation,
)
from woodchopping.ui.tournament_ui import (
    calculate_tournament_scenarios,
    distribute_competitors_into_heats,
    select_heat_advancers,
    fill_advancers_with_random_draw,
    generate_next_round,
    view_tournament_status,
    save_tournament_state,
    load_tournament_state,
    auto_save_state,
)
from woodchopping.ui.multi_event_ui import (
    create_multi_event_tournament,
    save_multi_event_tournament,
    load_multi_event_tournament,
    add_event_to_tournament,
    setup_tournament_roster,           # NEW V5.1
    assign_competitors_to_events,      # NEW V5.1
    view_wood_count,
    view_tournament_schedule,
    remove_event_from_tournament,
    calculate_all_event_handicaps,
    view_analyze_all_handicaps,
    approve_event_handicaps,
    generate_complete_day_schedule,
    sequential_results_workflow,
    generate_tournament_summary
)
from woodchopping.ui.v52_helpers import (    # NEW V5.1
    view_tournament_entries,
    edit_event_entries,
    manage_scratches
)
from woodchopping.handicaps import calculate_ai_enhanced_handicaps
from woodchopping.simulation import simulate_and_assess_handicaps
from woodchopping.ui.tournament_status import (
    display_tournament_progress_tracker,
    check_can_calculate_handicaps,
    check_can_generate_schedule,
)
from woodchopping.ui.error_display import (
    display_actionable_error,
    display_blocking_error,
    display_warning,
    display_success,
)
from woodchopping.ui.progress_ui import ProgressDisplay
from woodchopping.ui.entry_fee_tracker import (
    view_entry_fee_status,
)
from woodchopping.ui.scratch_management import (
    manage_tournament_scratches,
)

# Keep explanation system (educational tool)
import explanation_system_functions as explain

# STRATHEX Banner
try:
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━".center(68) + "║")
    print("║" + "S T R A T H E X".center(68) + "║")
    print("║" + "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("║" + "WOODCHOPPING HANDICAP CALCULATOR v5.2".center(68) + "║")
    print("║" + "Professional Competition System".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "═" * 68 + "╝")
except UnicodeEncodeError:
    # Fallback to ASCII banner if Unicode fails
    print("""
======================================================================

           STRATHEX - WOODCHOPPING HANDICAP CALCULATOR v5.2
                   Professional Competition System

======================================================================
""")
time.sleep(0.8)
#Load Competitor Data from Excel  full roster)
'''Read the xlsx file containing data. 
Sheet "competitors" contains competitor data
Sheet "wood" contains wood species data'''
try:
    comp_df = load_competitors_df()
except Exception as e:
    print(f"Error loading roster from Excel: {e}")
    comp_df = pd.DataFrame(columns=["competitor_name", "competitor_country"])

# Initialize STRATHMARK ResultStore and migrate historical Excel data (idempotent)
try:
    from strathmark.store import ResultStore as _ResultStore
    from woodchopping.data.store_registry import set_store as _set_store
    from woodchopping.strathmark_adapter import migrate_excel_to_store as _migrate
    _result_store = _ResultStore()
    _set_store(_result_store)
    _results_for_migration = load_results_df()
    _migrated_count = _migrate(_results_for_migration, _result_store)
    if _migrated_count > 0:
        print(f"  STRATHMARK: migrated {_migrated_count} historical results to persistent store.")
    del _results_for_migration, _migrated_count, _migrate
except Exception as _store_err:
    print(f"  Note: STRATHMARK store unavailable ({_store_err}). Predictions will use Excel only.")

#Wood Selection Dictionary - initialize with all expected keys
wood_selection = {
    "species": None, 
    "size_mm": None, 
    "quality": None,
    "event": None
}

# Heat assignment state (competitors selected for current heat) - LEGACY for backward compatibility
heat_assignment_df = pd.DataFrame()
heat_assignment_names = []

# Tournament State - NEW multi-round tournament system
tournament_state = {
    'event_name': None,                    # e.g., "SB Championship 2025"
    'num_stands': None,                    # e.g., 8 (number of available chopping stands)
    'tentative_competitors': None,         # User's estimate for planning
    'format': None,                        # "heats_to_finals" or "heats_to_semis_to_finals"
    'all_competitors': [],                 # List of competitor names in event
    'all_competitors_df': pd.DataFrame(),  # DataFrame of all competitors
    'rounds': [],                          # List of Round objects (heats, semis, finals)
    'current_round_index': 0,              # Active round index
    'capacity_info': {},                   # From calculate_tournament_scenarios()
    'handicap_results_all': [],            # Handicap results for all competitors
    'payout_config': None                  # Payout configuration dict (NEW V5.0)
}

# Multi-Event Tournament State - NEW for V5.0
multi_event_tournament_state = {
    'tournament_name': None,               # e.g., "Mason County Western Qualifier 2025"
    'date': None,                          # Tournament date
    'location': None,                      # Venue name
    'events': [],                          # List of event objects (each contains tournament_state)
    'current_event_index': 0,              # Active event being worked on
    'schedule': [],                        # Complete day schedule across all events
    'results': []                          # Final results across all events
}

## Competitor Selection Menu
''' Official will be presented with a list of competitors

    Definitions:
    'Roster'- list of all competitors available in the excel sheet
    'Heat Assignment'- list of competitors selected for the current heat

    1. Select Competitors for Heat from the roster
    2. Add competitors to the roster
    3. View Heat Assignment
    4. Remove competitors from the heat assignment
    5. Return to Main Menu
'''

## Wood Characteristics Menu
''' Official will be presented with a list of wood characteristics
    1. Select Wood Species from the list
    2. Enter Size in mm
    3. Enter wood quality 
    (0 for poor quality, 1-3 for soft, 4-7 for average firmness for species, 8-10 for above average firmness for species)
    4. Return to Main Menu
'''

##Select Event (SB/UH)
''' Official will be presented with two event codes to select from either SB or UH'''

## View Handicap Marks
''' Official will be presented with the calculated handicap marks for each selected competitor in the heat
    1. View Handicap Marks
    2. Return to Main Menu
'''


## Helper Functions for Bracket Menu
def get_wood_status_display(wood_selection: dict) -> str:
    """Generate wood configuration status string.

    Args:
        wood_selection: Wood configuration dictionary

    Returns:
        str: Formatted status string
    """
    from woodchopping.data import get_species_name_from_code

    species_code = wood_selection.get('species')
    diameter = wood_selection.get('size_mm')
    quality = wood_selection.get('quality')
    event = wood_selection.get('event')

    if species_code and diameter is not None and quality is not None and event:
        species_name = get_species_name_from_code(species_code)
        return f"[OK] {species_name}, {diameter}mm, Q{quality}, {event}"
    elif species_code or diameter or quality or event:
        return "[WARN] Partially configured (incomplete)"
    else:
        return "? Not configured"


def get_competitor_status_display(tournament_state: dict) -> str:
    """Generate competitor selection status string.

    Args:
        tournament_state: Tournament state dictionary

    Returns:
        str: Formatted status string
    """
    all_competitors = tournament_state.get('all_competitors', [])

    if all_competitors:
        count = len(all_competitors)
        return f"[OK] {count} competitor{'s' if count != 1 else ''} selected"
    else:
        return "? Not selected"


def display_bracket_status_tracker(wood_selection: dict, tournament_state: dict) -> None:
    """Display configuration status tracker for bracket menu.

    Args:
        wood_selection: Wood configuration dictionary
        tournament_state: Tournament state dictionary
    """
    print("\n" + "═" * 70)
    print("  CONFIGURATION STATUS")
    print("═" * 70)

    # Wood configuration status
    wood_status = get_wood_status_display(wood_selection)
    print(f"  Wood:        {wood_status}")

    # Competitor selection status
    comp_status = get_competitor_status_display(tournament_state)
    print(f"  Personnel:   {comp_status}")

    print("═" * 70)


def manage_bracket_competitors(tournament_state: dict, comp_df: pd.DataFrame, max_competitors: int = 999) -> dict:
    """Manage competitor selection for bracket tournament with add/remove/view options.

    Args:
        tournament_state: Tournament state dictionary
        comp_df: Full competitor roster DataFrame
        max_competitors: Maximum allowed competitors (999 for bracket mode)

    Returns:
        dict: Updated tournament_state
    """
    while True:
        print("\n╔" + "═" * 68 + "╗")
        print("║" + "MANAGE COMPETITORS".center(68) + "║")
        print("╚" + "═" * 68 + "╝")

        # Display current selection
        current_competitors = tournament_state.get('all_competitors', [])
        if current_competitors:
            print(f"\nCurrently selected: {len(current_competitors)} competitor(s)")
            print("-" * 70)
            for idx, name in enumerate(current_competitors, 1):
                print(f"  {idx:3d}) {name}")
            print("-" * 70)
        else:
            print("\nNo competitors currently selected.")

        # Menu options
        print("\nOPTIONS:")
        print("  1. Add competitors to selection")
        print("  2. Remove competitor from selection")
        print("  3. View full roster")
        print("  4. Clear all selections")
        print("  5. Return to bracket menu")
        print("=" * 70)

        choice = input("\nEnter your choice (1-5): ").strip()

        if choice == '1':
            # Add competitors
            print("\n" + "=" * 70)
            print("  ADD COMPETITORS")
            print("=" * 70)

            # Get already selected competitor names
            already_selected = set(current_competitors)

            # Display available competitors (not yet selected)
            available_df = comp_df[~comp_df['competitor_name'].isin(already_selected)].copy()

            if available_df.empty:
                print("\nAll competitors from roster are already selected!")
                input("\nPress Enter to continue...")
                continue

            print(f"\nAvailable competitors (not yet selected):")
            print("-" * 70)
            for idx in range(len(available_df)):
                row = available_df.iloc[idx]
                name = row.get("competitor_name", "Unknown")
                country = row.get("competitor_country", "Unknown")
                print(f"  {idx + 1:3d}) {name:35s} ({country})")

            print("\n" + "=" * 70)
            print("INSTRUCTIONS:")
            print("  - Enter single number: 5")
            print("  - Enter multiple numbers (comma-separated): 1,3,5,7")
            print("  - Enter range: 1-10")
            print("  - Combine: 1,3,5-8,12")
            print("  - Press Enter to cancel")
            print("=" * 70)

            selection = input("\nEnter competitor number(s): ").strip()

            if selection == "":
                print("No changes made.")
                continue

            # Parse selection
            new_indices = set()
            try:
                for part in selection.split(','):
                    part = part.strip()
                    if '-' in part:
                        start, end = part.split('-')
                        start_idx = int(start) - 1
                        end_idx = int(end) - 1
                        for i in range(start_idx, end_idx + 1):
                            if 0 <= i < len(available_df):
                                new_indices.add(i)
                    else:
                        idx = int(part) - 1
                        if 0 <= idx < len(available_df):
                            new_indices.add(idx)

                if new_indices:
                    # Add new competitors
                    new_competitors = available_df.iloc[sorted(new_indices)]['competitor_name'].tolist()
                    current_competitors.extend(new_competitors)

                    # Update tournament state
                    tournament_state['all_competitors'] = current_competitors
                    tournament_state['all_competitors_df'] = comp_df[comp_df['competitor_name'].isin(current_competitors)].copy()

                    print(f"\n[OK] {len(new_competitors)} competitor(s) added!")
                    for name in new_competitors:
                        print(f"  + {name}")
                else:
                    print("\nNo valid selections made.")

            except (ValueError, IndexError):
                print("\n[WARN] Invalid input format. No changes made.")

            input("\nPress Enter to continue...")

        elif choice == '2':
            # Remove competitor
            if not current_competitors:
                print("\nNo competitors to remove.")
                input("\nPress Enter to continue...")
                continue

            print("\n" + "=" * 70)
            print("  REMOVE COMPETITOR")
            print("=" * 70)

            print("\nCurrent selection:")
            for idx, name in enumerate(current_competitors, 1):
                print(f"  {idx:3d}) {name}")

            remove_input = input("\nEnter number to remove (or press Enter to cancel): ").strip()

            if remove_input == "":
                print("No changes made.")
                continue

            try:
                remove_idx = int(remove_input) - 1
                if 0 <= remove_idx < len(current_competitors):
                    removed_name = current_competitors.pop(remove_idx)

                    # Update tournament state
                    tournament_state['all_competitors'] = current_competitors
                    if current_competitors:
                        tournament_state['all_competitors_df'] = comp_df[comp_df['competitor_name'].isin(current_competitors)].copy()
                    else:
                        tournament_state['all_competitors_df'] = pd.DataFrame()

                    print(f"\n[OK] {removed_name} removed from selection")
                else:
                    print("\n[WARN] Invalid number")
            except ValueError:
                print("\n[WARN] Invalid input")

            input("\nPress Enter to continue...")

        elif choice == '3':
            # View full roster
            print("\n" + "=" * 70)
            print("  FULL COMPETITOR ROSTER")
            print("=" * 70)

            for idx in range(len(comp_df)):
                row = comp_df.iloc[idx]
                name = row.get("competitor_name", "Unknown")
                country = row.get("competitor_country", "Unknown")
                selected = "[OK]" if name in current_competitors else " "
                print(f" {selected} {idx + 1:3d}) {name:35s} ({country})")

            print("\n([OK] = Currently selected for bracket)")
            input("\nPress Enter to continue...")

        elif choice == '4':
            # Clear all selections
            if not current_competitors:
                print("\nNo competitors to clear.")
                input("\nPress Enter to continue...")
                continue

            confirm = input(f"\nClear all {len(current_competitors)} selections? (y/n): ").strip().lower()
            if confirm == 'y':
                tournament_state['all_competitors'] = []
                tournament_state['all_competitors_df'] = pd.DataFrame()
                print("\n[OK] All competitor selections cleared")
            else:
                print("\nCancelled.")

            input("\nPress Enter to continue...")

        elif choice == '5' or choice == '':
            # Return to bracket menu
            break

        else:
            print("\n[WARN] Invalid choice. Please enter 1-5.")
            input("\nPress Enter to continue...")

    return tournament_state


## Single Event Menu Function
def single_event_menu():
    """Menu for designing and running a single event"""
    global tournament_state, wood_selection, heat_assignment_df, heat_assignment_names, comp_df

    # Reset all state at the start of each new event to prevent data leakage
    # between consecutive tournament runs.
    tournament_state = {
        'event_name': None,
        'num_stands': None,
        'tentative_competitors': None,
        'format': None,
        'all_competitors': [],
        'all_competitors_df': pd.DataFrame(),
        'rounds': [],
        'current_round_index': 0,
        'capacity_info': {},
        'handicap_results_all': [],
        'payout_config': None,
    }
    wood_selection = {"species": None, "size_mm": None, "quality": None, "event": None}
    heat_assignment_df = pd.DataFrame()
    heat_assignment_names = []

    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        # Display banner based on tournament format
        if tournament_state.get('format') == 'bracket':
            # Bracket mode banner
            print("\n╔" + "═" * 68 + "╗")
            print("║" + " " * 68 + "║")
            print("║" + "BRACKET TOURNAMENT SYSTEM".center(68) + "║")
            print("║" + "Head-to-Head Championship Format".center(68) + "║")
            print("║" + " " * 68 + "║")
            print("╚" + "═" * 68 + "╝")

            # Display configuration status tracker
            display_bracket_status_tracker(wood_selection, tournament_state)
        else:
            # Regular handicap mode banner
            print("\n╔" + "═" * 68 + "╗")
            print("║" + " " * 68 + "║")
            print("║" + "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━".center(68) + "║")
            print("║" + "HANDICAP CALCULATION SYSTEM".center(68) + "║")
            print("║" + "AI-Powered Fair Competition".center(68) + "║")
            print("║" + "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━".center(68) + "║")
            print("║" + " " * 68 + "║")
            print("╚" + "═" * 68 + "╝")

        # Show current configuration status (including payouts)
        if tournament_state.get('event_name'):
            print(f"\nCurrent Event: {tournament_state['event_name']}")
            if tournament_state.get('payout_config'):
                from woodchopping.ui.payout_ui import display_payout_config
                print(f"  {display_payout_config(tournament_state['payout_config'])}")

        # Display menu based on tournament format
        if tournament_state.get('format') == 'bracket':
            # BRACKET MODE - Simplified menu
            print("\nTOURNAMENT SETUP:")
            print("  1. Manage Competitors (Add/Remove/View)")
            print("  2. Configure Event Payouts (Optional)")
            print("  3. Reconfigure Wood Characteristics")

            print("\nBRACKET OPERATIONS:")
            print("  4. Generate Bracket & Seeds")
            print("  5. View ASCII Bracket Tree")
            print("  6. Export Bracket to HTML (opens in browser)")
            print("  7. Enter Match Result")
            print("  8. View Current Round Details")

            print("\nSYSTEM:")
            print("  9. Save Event State")
            print(" 10. Return to Main Menu")
            print("=" * 70)
            menu_choice = input("\nEnter your choice (1-10): ").strip()
        else:
            # REGULAR HANDICAP MODE - Full menu
            print("\nTOURNAMENT SETUP:")
            print("  1. Configure Wood Characteristics")
            print("  2. Configure Tournament (Stands + Format)")
            print("  3. Select Competitors for Event")
            print("  4. Configure Event Payouts (Optional)")

            print("\nHANDICAP ANALYSIS:")
            print("  5. Calculate Handicaps for All Competitors")
            print("  6. View Handicaps & Fairness Analysis")
            print("  7. View Handicap Adjustment History")
            print("  8. View Prediction Accuracy Report")

            print("\nHEAT MANAGEMENT:")
            print("  9. Generate Initial Heats")
            print(" 10. Record Heat Results & Select Advancers")
            print(" 11. Generate Next Round (Semi/Final)")
            print(" 12. View Event Status")
            print(" 13. Print Schedule (Export to File)")
            print(" 14. View Final Results (with Payouts)")

            print("\nSYSTEM:")
            print(" 15. Save Event State")
            print(" 16. Return to Main Menu")
            print("=" * 70)
            menu_choice = input("\nEnter your choice (1-16): ").strip()

        # Map bracket mode choices to regular mode handlers
        if tournament_state.get('format') == 'bracket':
            # Bracket mode choice mapping:
            # 1 -> 3 (Select competitors)
            # 2 -> 4 (Configure payouts)
            # 3 -> 1 (Reconfigure wood) [NEW]
            # 4 -> 10 (Generate bracket)
            # 5 -> 11 (View ASCII tree)
            # 6 -> 12 (Export HTML)
            # 7 -> 13 (Enter match result)
            # 8 -> 14 (View round details)
            # 9 -> 15 (Save state)
            # 10 -> 16 (Return to menu)
            bracket_mapping = {'1': '3', '2': '4', '3': '1', '4': '10', '5': '11', '6': '12', '7': '13', '8': '14', '9': '15', '10': '16'}
            menu_choice = bracket_mapping.get(menu_choice, menu_choice)

        if menu_choice == '1':
            # Configure wood characteristics
            # Block if bracket has been generated (rounds exist)
            if tournament_state.get('format') == 'bracket':
                bracket_generated = (tournament_state.get('rounds') or
                                    tournament_state.get('winners_rounds'))
                if bracket_generated:
                    print("\n[WARN] ERROR: Cannot reconfigure wood after bracket generation")
                    print("   Wood characteristics are locked once bracket is created")
                    print("   Use Option 10 to return to main menu and start over")
                    input("\nPress Enter to return to menu...")
                    continue
            wood_selection = wood_menu(wood_selection)

        elif menu_choice == '2':
            # Configure Tournament (REGULAR MODE ONLY)
            # Block if bracket has been generated (rounds exist)
            if tournament_state.get('format') == 'bracket':
                bracket_generated = (tournament_state.get('rounds') or
                                    tournament_state.get('winners_rounds'))
                if bracket_generated:
                    print("\n[WARN] ERROR: Tournament configuration locked after bracket generation")
                    print("   Use Option 9 to return to main menu and start over")
                    input("\nPress Enter to return to menu...")
                    continue
            # Configure Tournament: stands + format
            print("\n" + "=" * 70)
            print("  CONFIGURE TOURNAMENT")
            print("=" * 70)

            try:
                num_stands = int(input("\nNumber of available stands: ").strip())
                tentative = int(input("Approximate number of competitors: ").strip())

                # Get event code first
                if not wood_selection.get('event'):
                    wood_selection = select_event_code(wood_selection)

                # Calculate scenarios
                scenarios = calculate_tournament_scenarios(num_stands, tentative)

                # Display all three scenarios
                print("\n" + "=" * 70)
                print("  SCENARIO 1: Single Heat Mode")
                print("=" * 70)
                print(scenarios['single_heat']['description'])
                print(f"\nTotal blocks needed: {scenarios['single_heat']['total_blocks']}")

                print("\n" + "=" * 70)
                print("  SCENARIO 2: Heats -> Finals")
                print("=" * 70)
                print(scenarios['heats_to_finals']['description'])
                print(f"\nTotal blocks needed: {scenarios['heats_to_finals']['total_blocks']}")

                print("\n" + "=" * 70)
                print("  SCENARIO 3: Heats -> Semis -> Finals")
                print("=" * 70)
                print(scenarios['heats_to_semis_to_finals']['description'])
                print(f"\nTotal blocks needed: {scenarios['heats_to_semis_to_finals']['total_blocks']}")

                print("\n" + "=" * 70)
                print("  SCENARIO 4: Head-to-Head Bracket")
                print("=" * 70)
                print("Single elimination bracket tournament")
                print("  -> Championship format (Mark 3 for all)")
                print("  -> Requires exactly 2 stands (head-to-head matches)")
                print("  -> AI-predicted seeding for fairness")
                print("  -> Automatic bye placement")
                print("  -> Visual bracket display + HTML export")
                print("\nBlocks needed: Based on number of matches (varies by bracket size)")

                # User selects format
                print("\n" + "=" * 70)
                format_choice = input("Select format (1, 2, 3, or 4): ").strip()

                if format_choice == '1':
                    tournament_state['format'] = 'single_heat'
                    tournament_state['capacity_info'] = scenarios['single_heat']
                elif format_choice == '2':
                    tournament_state['format'] = 'heats_to_finals'
                    tournament_state['capacity_info'] = scenarios['heats_to_finals']
                elif format_choice == '3':
                    tournament_state['format'] = 'heats_to_semis_to_finals'
                    tournament_state['capacity_info'] = scenarios['heats_to_semis_to_finals']
                elif format_choice == '4':
                    # Bracket mode - validate 2 stands
                    if num_stands != 2:
                        print("\n[WARN] Bracket mode requires exactly 2 stands (one head-to-head match at a time)")
                        force_2 = input("Continue with 2 stands? (y/n): ").strip().lower()
                        if force_2 == 'y':
                            num_stands = 2
                        else:
                            print("Bracket mode cancelled. Please reconfigure tournament.")
                            input("\nPress Enter to return to menu...")
                            continue

                    # NEW: Elimination type selection
                    print("\n" + "=" * 70)
                    print("  SELECT ELIMINATION TYPE")
                    print("=" * 70)
                    print("\n1. Single Elimination")
                    print("   - Lose once, you're out")
                    print("   - Faster tournament progression")
                    print("   - Traditional bracket format")
                    print("\n2. Double Elimination")
                    print("   - Lose twice to be eliminated")
                    print("   - Winners bracket + Losers bracket")
                    print("   - Grand finals (single match)")

                    elim_choice = input("\nSelect elimination type (1 or 2): ").strip()

                    if elim_choice == '2':
                        elimination_type = 'double'
                        print("\n[OK] Double elimination selected")
                    else:
                        elimination_type = 'single'
                        print("\n[OK] Single elimination selected")

                    from woodchopping.ui.bracket_ui import initialize_bracket_tournament
                    tournament_state = initialize_bracket_tournament(num_stands, tentative)
                    tournament_state['format'] = 'bracket'
                    tournament_state['elimination_type'] = elimination_type  # NEW FIELD

                    print(f"\n[OK] Bracket tournament initialized")
                    print(f"[OK] Format: {elimination_type.title()} elimination bracket")
                    print(f"[OK] Stands: 2 (head-to-head)")

                    # Skip capacity display for bracket - it supports unlimited competitors
                    # Continue to event name input below
                else:
                    print("Invalid choice. Tournament not configured.")
                    input("\nPress Enter to return to menu...")
                    continue

                tournament_state['num_stands'] = num_stands
                tournament_state['tentative_competitors'] = tentative

                # Prompt for event name
                event_name = input("\nEvent name (e.g., 'SB Championship 2025'): ").strip()
                tournament_state['event_name'] = event_name if event_name else "Unnamed Event"

                print(f"\n[OK] Tournament configured: {tournament_state['format']}")
                # Only show max competitors for non-bracket tournaments
                if tournament_state['format'] != 'bracket':
                    print(f"[OK] Max competitors: {tournament_state['capacity_info']['max_competitors']}")
                else:
                    print(f"[OK] Supports unlimited competitors with automatic byes")

            except ValueError:
                print("Invalid input. Please enter numbers.")

        elif menu_choice == '3':
            # Select ALL competitors for event
            if not tournament_state.get('num_stands'):
                print("\nERROR: Configure tournament first (Option 2)")
                input("\nPress Enter to return to menu...")
                continue

            # Bracket mode: Use enhanced competitor management with add/remove
            # Regular mode: Use simple select all interface
            if tournament_state['format'] == 'bracket':
                # Block if bracket has been generated (rounds exist)
                bracket_generated = (tournament_state.get('rounds') or
                                    tournament_state.get('winners_rounds'))
                if bracket_generated:
                    print("\n[WARN] ERROR: Cannot modify competitors after bracket generation")
                    print("   Competitor list is locked once bracket is created")
                    print("   Use Option 10 to return to main menu and start over")
                    input("\nPress Enter to return to menu...")
                    continue

                # Use enhanced competitor management for bracket mode
                tournament_state = manage_bracket_competitors(tournament_state, comp_df, max_competitors=999)
            else:
                # Regular handicap mode: Simple select all
                max_comp = tournament_state['capacity_info'].get('max_competitors')
                print(f"\nMaximum competitors for this format: {max_comp}")

                # Require event selection to enforce eligibility (must have event history)
                if not wood_selection.get('event'):
                    wood_selection = select_event_code(wood_selection)

                from woodchopping.data import load_results_df
                results_df = load_results_df()
                selected_df = select_all_event_competitors(
                    comp_df,
                    max_comp,
                    results_df=results_df,
                    event_code=wood_selection.get('event'),
                    wood_info=wood_selection
                )

                if not selected_df.empty:
                    tournament_state['all_competitors_df'] = selected_df
                    tournament_state['all_competitors'] = selected_df['competitor_name'].tolist()
                    print(f"\n[OK] {len(tournament_state['all_competitors'])} competitors selected for event")

        elif menu_choice == '4':
            # Configure Event Payouts (NEW V5.0)
            print("\n" + "=" * 70)
            print("  CONFIGURE EVENT PAYOUTS")
            print("=" * 70)

            if not tournament_state.get('all_competitors'):
                print("\nERROR: Select competitors first (Option 3)")
                input("\nPress Enter to return to menu...")
                continue

            from woodchopping.ui.payout_ui import configure_event_payouts, display_payout_config

            payout_config = configure_event_payouts()

            if payout_config:
                tournament_state['payout_config'] = payout_config
                print(f"\n[OK] Payout configuration saved")
                print(f"[OK] {display_payout_config(payout_config)}")
            else:
                print("\n[OK] Payout configuration skipped")

            input("\nPress Enter to return to menu...")

        elif menu_choice == '5':
            # Calculate handicaps for ALL competitors (regular tournament mode ONLY)
            # Comprehensive validation with helpful error messages
            missing = []

            # Check tournament configuration
            if not tournament_state.get('num_stands'):
                missing.append("  ? Tournament not configured (use Option 2)")

            # Check competitors
            if not tournament_state.get('all_competitors'):
                missing.append("  ? No competitors selected (use Option 3)")

            # Check wood characteristics
            if not wood_selection.get('species'):
                missing.append("  ? Wood species not selected (use Option 1)")

            if not wood_selection.get('size_mm'):
                missing.append("  ? Wood size (diameter) not set (use Option 1)")

            if wood_selection.get('quality') is None:
                missing.append("  ? Wood quality not set (use Option 1)")

            # Check event code
            if not wood_selection.get('event'):
                missing.append("  ✗ Event type not selected (SB/UH - use Option 1 or 3)")

            # If anything is missing, show comprehensive error
            if missing:
                box_width = 68
                print("\n╔" + "═" * box_width + "╗")

                # Center the title
                title = "⚠️ CANNOT CALCULATE HANDICAPS ⚠️"
                title_line = title.center(box_width)
                print("║" + title_line + "║")

                print("╠" + "═" * box_width + "╣")

                # Header line
                header = "Missing required information:".ljust(box_width)
                print("║" + header + "║")

                # Missing items
                for item in missing:
                    print("║" + item.ljust(box_width) + "║")

                print("╚" + "═" * box_width + "╝")
                print("\nPlease complete the missing items above, then try again.")
                input("\nPress Enter to return to menu...")
                continue

            progress_display = ProgressDisplay(
                title="HANDICAP CALCULATION IN PROGRESS",
                width=70,
                bar_length=40,
                item_label="competitors",
                detail_label="Analyzing"
            )
            progress_display.start()

            def show_progress(current, total, comp_name):
                """Display live progress bar with proper alignment"""
                progress_display.update(current, total, comp_name)

            # Use existing calculate_ai_enhanced_handicaps function with progress
            results_df = load_results_df()
            handicap_results = calculate_ai_enhanced_handicaps(
                tournament_state['all_competitors_df'],
                wood_selection['species'],
                wood_selection['size_mm'],
                wood_selection['quality'],
                wood_selection['event'],
                results_df,
                progress_callback=show_progress
            )

            progress_display.finish("All competitors analyzed successfully!")


            tournament_state['handicap_results_all'] = handicap_results

            # Store wood characteristics in tournament state for recalculation in later rounds
            tournament_state['wood_species'] = wood_selection['species']
            tournament_state['wood_diameter'] = wood_selection['size_mm']
            tournament_state['wood_quality'] = wood_selection['quality']
            tournament_state['event_code'] = wood_selection['event']

            # Success message with axe icon
            print("\n" + "=" * 70)
            print("    🪓  HANDICAP CALCULATION COMPLETE! 🪓")
            print(f"    [OK]  {len(handicap_results)} competitors analyzed")
            print("=" * 70)

        elif menu_choice == '6':
            # View handicaps + comprehensive analysis (NEW 5-PHASE FLOW - REGULAR MODE ONLY)
            if not tournament_state.get('handicap_results_all'):
                print("\nERROR: Calculate handicaps first (Option 5)")
                input("\nPress Enter to return to menu...")
                continue

            # PHASE 1: Display initial handicap marks with basic prediction table
            display_basic_prediction_table(
                tournament_state['handicap_results_all'],
                wood_selection
            )

            # PHASE 2: Monte Carlo fairness simulation
            run_mc = input("\nRun Monte Carlo fairness simulation? (y/n): ").strip().lower()
            if run_mc == 'y':
                simulate_and_assess_handicaps(tournament_state['handicap_results_all'])

            # PHASE 3: Comprehensive AI Analysis of Predictions
            show_analysis = input("\nView detailed AI analysis of prediction methods? (y/n): ").strip().lower()
            if show_analysis == 'y':
                try:
                    display_comprehensive_prediction_analysis(
                        tournament_state['handicap_results_all'],
                        wood_selection
                    )
                except Exception as e:
                    print(f"\n[WARN] Error during AI analysis: {e}")
                    print("Continuing without AI analysis...")

            # PHASE 4: Optional explanation of handicap calculations
            show_calc = input("\nView explanation of how handicaps are calculated? (y/n): ").strip().lower()
            if show_calc == 'y':
                display_handicap_calculation_explanation()

            # PHASE 5: Judge approval workflow
            print("\n" + "="*70)
            print("  HANDICAP APPROVAL")
            print("="*70)
            print("\n1. Accept handicaps as calculated")
            print("2. Manually adjust individual handicaps")

            approval_choice = input("\nYour choice (1 or 2): ").strip()

            if approval_choice == '2':
                # Manual adjustment workflow
                adjusted_results, initials, timestamp = manual_adjust_handicaps(
                    tournament_state['handicap_results_all'],
                    wood_selection
                )

                if initials:  # Adjustment approved
                    # Update with adjusted marks
                    tournament_state['handicap_results_all'] = adjusted_results

                    # A5: Log all manual adjustments to tournament_state
                    for result in adjusted_results:
                        if result.get('manual_adjustment'):
                            log_handicap_adjustment(
                                tournament_state=tournament_state,
                                competitor_name=result['name'],
                                original_mark=result.get('original_mark', result['mark']),
                                adjusted_mark=result['mark'],
                                reason=result.get('adjustment_reason', 'No reason provided'),
                                adjustment_type='manual'
                            )

                    # Store approval metadata
                    for result in adjusted_results:
                        result['approved_by'] = initials
                        result['approved_at'] = timestamp
                    print(f"\n[OK] Handicaps approved by {initials} at {timestamp}")
                else:
                    print("\n[WARN] Adjustment cancelled - handicaps NOT approved")

            elif approval_choice == '1':
                # Accept as calculated - still requires approval
                initials, timestamp = judge_approval()

                if initials:  # Accepted and approved
                    for result in tournament_state['handicap_results_all']:
                        result['approved_by'] = initials
                        result['approved_at'] = timestamp
                    print(f"\n[OK] Handicaps approved by {initials} at {timestamp}")
                else:
                    print("\n[WARN] Approval cancelled - handicaps NOT approved")
            else:
                print("\n[WARN] Invalid choice - handicaps NOT approved")

        elif menu_choice == '7':
            # View Handicap Adjustment History (A5 - REGULAR MODE ONLY)
            view_adjustment_history(tournament_state)

        elif menu_choice == '8':
            # View Prediction Accuracy Report (B1 - REGULAR MODE ONLY)
            completed_rounds = [r for r in tournament_state.get('rounds', []) if r['status'] == 'completed']

            if not completed_rounds:
                print("\nNo completed rounds to analyze.")
                print("Complete at least one round first to view prediction accuracy.")
                input("\nPress Enter to continue...")
            else:
                print("\n╔" + "═" * 68 + "╗")
                print("║" + "PREDICTION ACCURACY ANALYSIS".center(68) + "║")
                print("╚" + "═" * 68 + "╝")

                for round_obj in completed_rounds:
                    # Analyze accuracy
                    accuracy_data = analyze_prediction_accuracy(round_obj)

                    # Format and display report
                    report = format_prediction_accuracy_report(round_obj['round_name'], accuracy_data)
                    print(report)

                    # Store accuracy data in tournament state for future reference
                    if 'prediction_accuracy_log' not in tournament_state:
                        tournament_state['prediction_accuracy_log'] = []

                    tournament_state['prediction_accuracy_log'].append({
                        'round_name': round_obj['round_name'],
                        'analysis': accuracy_data,
                        'timestamp': datetime.now().isoformat(timespec='seconds')
                    })

                input("\nPress Enter to continue...")

        elif menu_choice == '9':
            # Generate initial heats (REGULAR MODE ONLY)
            if tournament_state.get('format') == 'bracket':
                print("\nERROR: This option is for handicap tournaments only")
                print("For bracket tournaments, use Option 10 to generate bracket")
                input("\nPress Enter to return to menu...")
                continue

            if not tournament_state.get('handicap_results_all'):
                print("\nERROR: Calculate handicaps first (Option 5)")
                input("\nPress Enter to return to menu...")
                continue

            # Check if heats already exist
            if tournament_state.get('rounds'):
                print("\n" + "=" * 70)
                print("  [WARN] WARNING: HEATS ALREADY EXIST")
                print("=" * 70)
                print(f"\nExisting heats: {len(tournament_state['rounds'])} heat(s)")
                regenerate = input("\nRegenerate heats? This will OVERWRITE existing assignments (y/n): ").strip().lower()
                if regenerate != 'y':
                    print("\n[OK] Heat generation cancelled")
                    input("\nPress Enter to return to menu...")
                    continue

            num_competitors = len(tournament_state['all_competitors'])
            num_stands = tournament_state['num_stands']

            # Check if single heat mode
            if tournament_state.get('format') == 'single_heat':
                print(f"\nGenerating single heat for training/testing...")

                # Create single heat with all competitors
                heats = [{
                    'round_name': 'Heat 1',
                    'round_type': 'heat',
                    'competitors': tournament_state['all_competitors'],
                    'handicap_results': tournament_state['handicap_results_all'],
                    'num_to_advance': 0,  # No advancement in single heat mode
                    'status': 'pending',
                    'actual_results': {},
                    'advancers': []
                }]

                tournament_state['rounds'] = heats

                # Display heat assignment
                print(f"\n{'='*70}")
                print(f"  SINGLE HEAT - TRAINING/TESTING MODE")
                print(f"{'='*70}")
                print(f"\nHeat 1 ({len(heats[0]['competitors'])} competitors - No advancement):")
                for i, name in enumerate(heats[0]['competitors'], 1):
                    mark = next((c['mark'] for c in heats[0]['handicap_results'] if c['name'] == name), '?')
                    print(f"  {i}) {name:35s} (Mark {mark})")
                print(f"{'='*70}")
                print("\n[OK] Results can be recorded and saved to build historical data")
            else:
                # Multi-round tournament mode
                # Use optimal stands_per_heat from capacity calculation (may be less than total num_stands)
                capacity_info = tournament_state['capacity_info']
                stands_per_heat = capacity_info.get('stands_per_heat', num_stands)  # Fallback to num_stands for old saved states
                num_heats = capacity_info['num_heats']
                print(f"\nGenerating {num_heats} heats of {stands_per_heat} with balanced skill distribution...")

                heats = distribute_competitors_into_heats(
                    tournament_state['all_competitors_df'],
                    tournament_state['handicap_results_all'],
                    stands_per_heat,  # Use optimal stands per heat, not total available stands
                    num_heats
                )

                tournament_state['rounds'] = heats

                # Display heat assignments
                print(f"\n{'='*70}")
                print(f"  HEAT ASSIGNMENTS")
                print(f"{'='*70}")
                for heat in heats:
                    print(f"\n{heat['round_name']} ({len(heat['competitors'])} competitors, top {heat['num_to_advance']} advance):")
                    for i, name in enumerate(heat['competitors'], 1):
                        # Find mark for this competitor
                        mark = next((c['mark'] for c in heat['handicap_results'] if c['name'] == name), '?')
                        print(f"  {i}) {name:35s} (Mark {mark})")
                print(f"{'='*70}")

            # Auto-save
            auto_save_state(tournament_state)
            print("\n[OK] Tournament state auto-saved")
            input("\nPress Enter to return to menu...")

        elif menu_choice == '10':
            # Option 10: Record Heat Results (REGULAR MODE) or Generate Bracket (BRACKET MODE)
            if tournament_state.get('format') == 'bracket':
                # BRACKET MODE: Generate Bracket & Seeds
                from woodchopping.ui.bracket_ui import (
                    generate_bracket_seeds,
                    generate_bracket_with_byes,
                    generate_double_elimination_bracket
                )

                # Validation
                missing = []
                if not tournament_state.get('all_competitors'):
                    missing.append("  ? No competitors selected (use Option 3)")
                if not wood_selection.get('species'):
                    missing.append("  ? Wood species not selected (use Option 1)")
                if not wood_selection.get('size_mm'):
                    missing.append("  ? Wood diameter not set (use Option 1)")
                if wood_selection.get('quality') is None:
                    missing.append("  ? Wood quality not set (use Option 1)")
                if not wood_selection.get('event'):
                    missing.append("  ✗ Event type not selected (use Option 1)")

                if missing:
                    print("\n╔" + "═" * 68 + "╗")
                    print("║" + "⚠️ CANNOT GENERATE BRACKET ⚠️".center(68) + "║")
                    print("╠" + "═" * 68 + "╣")
                    print("║" + "Missing required information:".ljust(68) + "║")
                    for item in missing:
                        print("║" + item.ljust(68) + "║")
                    print("╚" + "═" * 68 + "╝")
                    input("\nPress Enter to return to menu...")
                    continue

                # Store wood configuration in bracket state
                tournament_state['wood_species'] = wood_selection['species']
                tournament_state['wood_diameter'] = wood_selection['size_mm']
                tournament_state['wood_quality'] = wood_selection['quality']
                tournament_state['event_code'] = wood_selection['event']

                elimination_type = tournament_state.get('elimination_type', 'single')

                print("\n╔" + "═" * 68 + "╗")
                print("║" + f"GENERATING {elimination_type.upper()} ELIMINATION BRACKET".center(68) + "║")
                print("╚" + "═" * 68 + "╝\n")

                # Generate predictions for seeding
                predictions = generate_bracket_seeds(
                    tournament_state['all_competitors_df'],
                    wood_selection['species'],
                    wood_selection['size_mm'],
                    wood_selection['quality'],
                    wood_selection['event']
                )

                tournament_state['predictions'] = predictions
                tournament_state['num_competitors'] = len(predictions)

                # Generate bracket structure based on elimination type
                if elimination_type == 'double':
                    # Double elimination
                    bracket_data = generate_double_elimination_bracket(predictions)
                    tournament_state['winners_rounds'] = bracket_data['winners_rounds']
                    tournament_state['losers_rounds'] = bracket_data['losers_rounds']
                    tournament_state['grand_finals'] = bracket_data['grand_finals']
                    tournament_state['total_rounds'] = bracket_data['total_rounds']
                    tournament_state['total_matches'] = bracket_data['total_matches']
                    tournament_state['eliminated'] = []  # Track eliminated competitors

                    print(f"\n[OK] Double elimination bracket generated successfully!")
                    print(f"  Competitors: {tournament_state['num_competitors']}")
                    print(f"  Winners Bracket Rounds: {len(bracket_data['winners_rounds'])}")
                    print(f"  Losers Bracket Rounds: {len(bracket_data['losers_rounds'])}")
                    print(f"  Total Matches: {tournament_state['total_matches']}")
                else:
                    # Single elimination
                    rounds = generate_bracket_with_byes(predictions)
                    tournament_state['rounds'] = rounds
                    tournament_state['total_rounds'] = len(rounds)

                    # Calculate total matches
                    total_matches = sum(len(r['matches']) for r in rounds)
                    tournament_state['total_matches'] = total_matches

                    print(f"\n[OK] Single elimination bracket generated successfully!")
                    print(f"  Competitors: {tournament_state['num_competitors']}")
                    print(f"  Total Rounds: {tournament_state['total_rounds']}")
                    print(f"  Total Matches: {tournament_state['total_matches']}")

                print(f"\nSeeding complete - fastest predicted time = Seed 1")
                input("\nPress Enter to return to menu...")
                continue

            # REGULAR MODE: Record Heat Results & Select Advancers
            if not tournament_state.get('rounds'):
                print("\nERROR: Generate heats first (Option 9)")
                input("\nPress Enter to return to menu...")
                continue

            pending = [r for r in tournament_state['rounds'] if r['status'] == 'pending']
            in_progress = [r for r in tournament_state['rounds'] if r['status'] == 'in_progress']
            available = pending + in_progress

            if not available:
                print("\nAll heats in current round completed!")
                print("Use Option 11 to generate next round.")
                input("\nPress Enter to return to menu...")
                continue

            # Select heat to record
            print(f"\n{'='*70}")
            print(f"  SELECT HEAT TO RECORD")
            print(f"{'='*70}")
            for i, heat in enumerate(available, 1):
                status = "[WARN] In Progress" if heat['status'] == 'in_progress' else "[ ] Pending"
                print(f"{i}) {heat['round_name']:15s} - {len(heat['competitors'])} competitors ({status})")

            try:
                heat_choice = int(input("\nSelect heat to record (number): ").strip()) - 1
                selected_heat = available[heat_choice]

                # Record times
                print(f"\n{'='*70}")
                print(f"  RECORDING RESULTS FOR {selected_heat['round_name']}")
                print(f"{'='*70}")
                append_results_to_excel(
                    heat_assignment_df,
                    wood_selection,
                    round_object=selected_heat,
                    tournament_state=tournament_state
                )

                # Select advancers
                if tournament_state.get('format') == 'single_heat':
                    selected_heat['status'] = 'completed'
                    selected_heat['advancers'] = []
                    print(f"\n[OK] {selected_heat['round_name']} completed")
                    print("[OK] Results saved to historical data")
                else:
                    advancers = select_heat_advancers(selected_heat)
                    print(f"\n[OK] {selected_heat['round_name']} completed")
                    print(f"[OK] Advancers: {', '.join(advancers)}")

                auto_save_state(tournament_state)

            except (ValueError, IndexError):
                print("Invalid selection.")

        elif menu_choice == '11':
            # Option 11: View ASCII Bracket Tree (BRACKET MODE) or Generate Next Round (REGULAR MODE)
            if tournament_state.get('format') == 'bracket':
                # BRACKET MODE: View ASCII Bracket Tree
                from woodchopping.ui.bracket_ui import render_bracket_tree_ascii, render_double_elim_bracket_ascii

                # Check if bracket generated
                if tournament_state.get('elimination_type') == 'double':
                    if not tournament_state.get('winners_rounds'):
                        print("\nERROR: Generate bracket first (Option 10)")
                        input("\nPress Enter to return to menu...")
                        continue
                    render_double_elim_bracket_ascii(tournament_state)
                else:
                    if not tournament_state.get('rounds'):
                        print("\nERROR: Generate bracket first (Option 10)")
                        input("\nPress Enter to return to menu...")
                        continue
                    render_bracket_tree_ascii(tournament_state)

                input("\nPress Enter to return to menu...")
                continue

            # REGULAR MODE: Generate Next Round (Semi/Final)
            if not tournament_state.get('rounds'):
                print("\nERROR: No tournament rounds exist yet")
                input("\nPress Enter to return to menu...")
                continue

            current_rounds = tournament_state['rounds']
            incomplete = [r for r in current_rounds if r['status'] != 'completed']

            if incomplete:
                print(f"\nERROR: {len(incomplete)} heat(s) not yet completed:")
                for heat in incomplete:
                    print(f"  - {heat['round_name']}")
                print("\nComplete all heats before generating next round.")
                input("\nPress Enter to return to menu...")
                continue

            all_advancers = []
            for heat in current_rounds:
                all_advancers.extend(heat.get('advancers', []))

            print(f"\n{len(all_advancers)} competitors advancing to next round:")
            for name in all_advancers:
                print(f"  - {name}")

            current_type = current_rounds[0]['round_type']
            tournament_format = tournament_state.get('format')

            if current_type == 'heat':
                if tournament_format == 'heats_to_finals':
                    next_type = 'final'
                else:
                    next_type = 'semi'
            elif current_type == 'semi':
                next_type = 'final'
            else:
                print("\nTournament already has finals generated!")
                input("\nPress Enter to return to menu...")
                continue

            target_count = None
            if next_type == 'final':
                target_count = tournament_state.get('num_stands')
            elif next_type == 'semi':
                num_semis = tournament_state.get('capacity_info', {}).get('num_semis', 2)
                if tournament_state.get('num_stands'):
                    target_count = tournament_state['num_stands'] * num_semis

            all_advancers = fill_advancers_with_random_draw(
                current_rounds,
                all_advancers,
                target_count,
                round_label=next_type
            )

            print(f"\nGenerating {next_type} round...")
            next_rounds = generate_next_round(
                tournament_state,
                all_advancers,
                next_type,
                is_championship=False,
                animate_selection=True
            )
            tournament_state['rounds'].extend(next_rounds)

            print(f"\n[OK] {len(next_rounds)} {next_type} heat(s) generated")
            for round_obj in next_rounds:
                print(f"\n{round_obj['round_name']} ({len(round_obj['competitors'])} competitors):")
                for name in round_obj['competitors']:
                    print(f"  - {name}")

            auto_save_state(tournament_state)

        elif menu_choice == '12':
            # Option 12: Export Bracket to HTML (BRACKET MODE) or View Event Status (REGULAR MODE)
            if tournament_state.get('format') == 'bracket':
                # BRACKET MODE: Export Bracket to HTML
                from woodchopping.ui.bracket_ui import export_bracket_to_html, open_bracket_in_browser
                if not tournament_state.get('rounds'):
                    print("\nERROR: Generate bracket first (Option 10)")
                    input("\nPress Enter to return to menu...")
                    continue
                print("\n╔" + "═" * 68 + "╗")
                print("║" + "EXPORTING BRACKET TO HTML".center(68) + "║")
                print("╚" + "═" * 68 + "╝\n")
                html_file = export_bracket_to_html(tournament_state)
                open_bracket_in_browser(html_file)
                print(f"\n[OK] Bracket exported to: {html_file}")
                print(f"[OK] Opened in browser automatically")
                input("\nPress Enter to return to menu...")
                continue

            # REGULAR MODE: View Event Status
            view_tournament_status(tournament_state)

        elif menu_choice == '13':
            # Option 13: Enter Match Result (BRACKET MODE) or Print Schedule (REGULAR MODE)
            if tournament_state.get('format') == 'bracket':
                # BRACKET MODE: Enter Match Result
                from woodchopping.ui.bracket_ui import sequential_match_entry_workflow
                if not tournament_state.get('rounds'):
                    print("\nERROR: Generate bracket first (Option 10)")
                    input("\nPress Enter to return to menu...")
                    continue
                tournament_state = sequential_match_entry_workflow(tournament_state)
                continue

            # REGULAR MODE: Print Schedule (Export to File)
            if not tournament_state.get('rounds'):
                print("\nERROR: No rounds to print. Generate heats first (Option 9)")
                input("\nPress Enter to return to menu...")
            else:
                display_and_export_schedule(tournament_state)

        elif menu_choice == '14':
            # Option 14: View Current Round Details (BRACKET MODE) or View Final Results (REGULAR MODE)
            if tournament_state.get('format') == 'bracket':
                # BRACKET MODE: View Current Round Details
                from woodchopping.ui.bracket_ui import render_round_section
                if not tournament_state.get('rounds'):
                    print("\nERROR: Generate bracket first (Option 10)")
                    input("\nPress Enter to return to menu...")
                    continue
                current_round = tournament_state.get('current_round_number', 1)
                render_round_section(tournament_state, current_round)
                input("\nPress Enter to return to menu...")
                continue

            # REGULAR MODE: View Final Results (with Payouts)
            from woodchopping.ui.payout_ui import display_single_event_final_results
            display_single_event_final_results(tournament_state)

        elif menu_choice == '15':
            # Save Event State (BOTH MODES)
            save_tournament_state(tournament_state, "saves/tournament_state.json")

        elif menu_choice == '16':
            # Return to Main Menu (BOTH MODES)
            print("\nReturning to main menu...")
            break

        else:
            print("Invalid selection. Try again.")


## Multi-Event Tournament Menu Function
def multi_event_tournament_menu():
    """Menu for designing and running multi-event tournaments"""
    global multi_event_tournament_state, comp_df

    while True:
        # Display progress tracker if tournament exists
        if multi_event_tournament_state.get('tournament_name'):
            display_tournament_progress_tracker(multi_event_tournament_state)
        else:
            # Show banner only if no tournament
            print("\n╔" + "═" * 68 + "╗")
            print("║" + " " * 68 + "║")
            print("║" + "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━".center(68) + "║")
            print("║" + "TOURNAMENT MANAGEMENT SYSTEM".center(68) + "║")
            print("║" + "Multi-Event Handicapping".center(68) + "║")
            print("║" + "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━".center(68) + "║")
            print("║" + "◆ STRATHEX ◆".center(68) + "║")
            print("║" + " " * 68 + "║")
            print("╚" + "═" * 68 + "╝")

        print("\nSETUP PHASE:")
        print("  1. Create New Tournament")
        print("  2. Define All Events (Add/Remove/View)")
        print("  3. Setup Tournament Roster (All Competitors)")
        print("  4. Assign Competitors to Events")
        print("  5. Manage Entry Fees & Payouts")
        print("\nPRE-COMPETITION:")
        print("  6. Calculate All Handicaps (Batch)")
        print("  7. Review & Analyze Handicaps")
        print("  8. Approve Handicaps (by Event)")
        print("  9. Generate Complete Day Schedule")
        print("\nDAY-OF OPERATIONS:")
        print(" 10. Manage Scratches/Withdrawals")
        print(" 11. Begin Competition (Results Entry)")
        print(" 12. View Live Tournament Status")
        print(" 13. Print/Export Schedules")
        print("\nCOMPLETION:")
        print(" 14. Generate Final Summary")
        print(" 15. View Earnings Report")
        print("\nSYSTEM:")
        print(" 16. View Wood Count")
        print(" 17. Save Tournament")
        print(" 18. Return to Main Menu")
        print("=" * 70)
        print("\nQuick shortcuts: 's' = save, 'q' = quit, 'h' = help")

        menu_choice = input("\nEnter your choice (1-18 or shortcut): ").strip().lower()

        # Handle keyboard shortcuts
        if menu_choice == 's':
            # Quick save
            if multi_event_tournament_state.get('tournament_name'):
                from woodchopping.ui.multi_event_ui import auto_save_multi_event
                auto_save_multi_event(multi_event_tournament_state)
                display_success("Tournament saved successfully")
            else:
                print("\n[WARN] No tournament to save")
                input("\nPress Enter to continue...")
            continue

        elif menu_choice == 'q' or menu_choice == 'x':
            # Quick exit to main menu
            if display_warning("Exit Tournament Menu", "Return to main menu?", confirmation=True):
                break
            continue

        elif menu_choice == 'h':
            # Help - show what each option does
            print("\n╔" + "═" * 68 + "╗")
            print("║" + "HELP - Tournament Workflow".center(68) + "║")
            print("╠" + "═" * 68 + "╣")
            print("║" + "1. Start by creating a new tournament".ljust(68) + "║")
            print("║" + "2. Define all events (wood, format, etc.)".ljust(68) + "║")
            print("║" + "3. Select all competitors for the day".ljust(68) + "║")
            print("║" + "4. Assign each competitor to their events".ljust(68) + "║")
            print("║" + "5. (Optional) Configure prize money/payouts".ljust(68) + "║")
            print("║" + "6-8. Calculate and approve handicaps".ljust(68) + "║")
            print("║" + "9. Generate the complete day schedule".ljust(68) + "║")
            print("║" + "10. Handle day-of scratches/withdrawals".ljust(68) + "║")
            print("║" + "11-13. Run competition and track results".ljust(68) + "║")
            print("║" + "14-15. View final summaries and earnings".ljust(68) + "║")
            print("╚" + "═" * 68 + "╝")
            input("\nPress Enter to continue...")
            continue

        if menu_choice == '1':
            # Create New Tournament
            multi_event_tournament_state = create_multi_event_tournament()

        elif menu_choice == '2':
            # Define All Events (Add/Remove/View) - NEW SUBMENU
            if not multi_event_tournament_state.get('tournament_name'):
                choice = display_actionable_error(
                    "CANNOT MANAGE EVENTS",
                    "Tournament must be created first.",
                    quick_action="create tournament now",
                    quick_action_key="1"
                )
                if choice == '1':
                    multi_event_tournament_state = create_multi_event_tournament()
                continue

            # Event management submenu loop
            while True:
                print("\n╔" + "═" * 68 + "╗")
                print("║" + "EVENT MANAGEMENT".center(68) + "║")
                print("╠" + "═" * 68 + "╣")
                print("║" + f"Tournament: {multi_event_tournament_state['tournament_name']}".ljust(68) + "║")
                print("║" + f"Current events: {len(multi_event_tournament_state.get('events', []))}".ljust(68) + "║")
                print("╠" + "═" * 68 + "╣")
                print("║" + "  1. Add New Event".ljust(68) + "║")
                print("║" + "  2. Remove Event".ljust(68) + "║")
                print("║" + "  3. View Wood Count".ljust(68) + "║")
                print("║" + "  4. Return to Main Menu".ljust(68) + "║")
                print("╚" + "═" * 68 + "╝")

                event_choice = input("\nChoice [1-4]: ").strip()

                if event_choice == '1':
                    results_df = load_results_df()
                    multi_event_tournament_state = add_event_to_tournament(
                        multi_event_tournament_state,
                        comp_df,
                        results_df
                    )
                elif event_choice == '2':
                    if not multi_event_tournament_state.get('events'):
                        print("\n[WARN] No events to remove")
                        input("\nPress Enter to continue...")
                    else:
                        multi_event_tournament_state = remove_event_from_tournament(
                            multi_event_tournament_state
                        )
                elif event_choice == '3':
                    if not multi_event_tournament_state.get('events'):
                        print("\n[WARN] No events to count")
                        input("\nPress Enter to continue...")
                    else:
                        view_wood_count(multi_event_tournament_state)
                elif event_choice == '4':
                    break  # Exit to main menu
                else:
                    print("\n[WARN] Invalid choice")
                    input("\nPress Enter to continue...")

        elif menu_choice == '3':
            # Setup Tournament Roster
            if not multi_event_tournament_state.get('tournament_name'):
                choice = display_actionable_error(
                    "CANNOT SETUP ROSTER",
                    "Tournament must be created first.",
                    quick_action="create tournament now",
                    quick_action_key="1"
                )
                if choice == '1':
                    multi_event_tournament_state = create_multi_event_tournament()
                continue

            multi_event_tournament_state = setup_tournament_roster(
                multi_event_tournament_state,
                comp_df
            )

        elif menu_choice == '4':
            # Assign Competitors to Events
            if not multi_event_tournament_state.get('tournament_roster'):
                choice = display_actionable_error(
                    "CANNOT ASSIGN COMPETITORS",
                    "Tournament roster must be configured first.",
                    quick_action="setup roster now",
                    quick_action_key="3"
                )
                if choice == '3':
                    multi_event_tournament_state = setup_tournament_roster(
                        multi_event_tournament_state,
                        comp_df
                    )
                continue

            multi_event_tournament_state = assign_competitors_to_events(
                multi_event_tournament_state
            )

        elif menu_choice == '5':
            # Entry Fee Management & Payouts Submenu
            if not multi_event_tournament_state.get('tournament_name'):
                display_actionable_error(
                    "CANNOT MANAGE FINANCES",
                    "Tournament must be created first.",
                    quick_action="create tournament now",
                    quick_action_key="1"
                )
                if choice == '1':
                    multi_event_tournament_state = create_multi_event_tournament()
                continue

            # Submenu loop for entry fees and payouts
            while True:
                print("\n╔" + "═" * 68 + "╗")
                print("║" + "TOURNAMENT FINANCES".center(68) + "║")
                print("╠" + "═" * 68 + "╣")
                print("║" + f"Tournament: {multi_event_tournament_state['tournament_name']}".ljust(68) + "║")

                # Show fee tracking status
                if multi_event_tournament_state.get('entry_fee_tracking_enabled'):
                    print("║" + "Entry Fee Tracking: ENABLED".ljust(68) + "║")
                else:
                    print("║" + "Entry Fee Tracking: DISABLED".ljust(68) + "║")

                print("╠" + "═" * 68 + "╣")
                print("║" + "  1. View Entry Fee Status".ljust(68) + "║")
                print("║" + "  2. Mark Fees as Paid".ljust(68) + "║")
                print("║" + "  3. Configure Event Payouts".ljust(68) + "║")
                print("║" + "  4. Return to Main Menu".ljust(68) + "║")
                print("╚" + "═" * 68 + "╝")

                finance_choice = input("\nChoice [1-4]: ").strip()

                if finance_choice == '1' or finance_choice == '2':
                    view_entry_fee_status(multi_event_tournament_state)
                elif finance_choice == '3':
                    from woodchopping.ui.payout_ui import configure_tournament_payouts
                    multi_event_tournament_state = configure_tournament_payouts(multi_event_tournament_state)
                elif finance_choice == '4':
                    break  # Exit to main menu
                else:
                    print("\n[WARN] Invalid choice")
                    input("\nPress Enter to continue...")

        elif menu_choice == '6':
            # Calculate All Handicaps (BATCH)
            # Use validation module
            can_proceed, errors = check_can_calculate_handicaps(multi_event_tournament_state)

            if not can_proceed:
                display_blocking_error("CANNOT CALCULATE HANDICAPS", errors)
                continue

            results_df = load_results_df()
            multi_event_tournament_state = calculate_all_event_handicaps(
                multi_event_tournament_state,
                results_df
            )

        elif menu_choice == '7':
            # Review & Analyze Handicaps
            if not multi_event_tournament_state.get('events'):
                display_actionable_error(
                    "CANNOT VIEW HANDICAPS",
                    "No events in tournament. Add events first (Option 2).",
                )
                continue

            view_analyze_all_handicaps(multi_event_tournament_state)

        elif menu_choice == '8':
            # Approve Handicaps (by Event)
            if not multi_event_tournament_state.get('events'):
                display_actionable_error(
                    "CANNOT APPROVE HANDICAPS",
                    "No events in tournament. Add events first (Option 2).",
                )
                continue

            approve_event_handicaps(multi_event_tournament_state)

        elif menu_choice == '9':
            # Generate Complete Day Schedule
            # Use validation module
            can_proceed, errors = check_can_generate_schedule(multi_event_tournament_state)

            if not can_proceed:
                display_blocking_error("CANNOT GENERATE SCHEDULE", errors)
                continue

            multi_event_tournament_state = generate_complete_day_schedule(
                multi_event_tournament_state
            )

        elif menu_choice == '10':
            # Manage Scratches/Withdrawals - FULLY IMPLEMENTED
            if not multi_event_tournament_state.get('tournament_roster'):
                display_actionable_error(
                    "CANNOT MANAGE SCRATCHES",
                    "Tournament roster must be configured first.",
                    quick_action="setup roster now",
                    quick_action_key="3"
                )
                continue

            multi_event_tournament_state = manage_tournament_scratches(
                multi_event_tournament_state
            )

        elif menu_choice == '11':
            # Begin Sequential Results Entry
            if not multi_event_tournament_state.get('events'):
                print("\nERROR: Generate day schedule first (Option 10)")
                input("\nPress Enter to return to menu...")
                continue

            multi_event_tournament_state = sequential_results_workflow(
                multi_event_tournament_state,
                wood_selection,      # Legacy parameter
                heat_assignment_df   # Legacy parameter
            )

        elif menu_choice == '12':
            # View Tournament Status
            if not multi_event_tournament_state.get('tournament_name'):
                print("\nERROR: Create tournament first (Option 1)")
                input("\nPress Enter to return to menu...")
                continue

            view_tournament_schedule(multi_event_tournament_state)

        elif menu_choice == '13':
            # Print Schedule (Export to File) - NEW V5.0
            if not multi_event_tournament_state.get('events'):
                print("\nERROR: No events to print. Add events first (Option 2)")
                input("\nPress Enter to return to menu...")
            else:
                display_and_export_schedule(multi_event_tournament_state)

        elif menu_choice == '14':
            # Generate Final Tournament Summary
            if not multi_event_tournament_state.get('events'):
                print("\nERROR: No events completed yet")
                input("\nPress Enter to return to menu...")
                continue

            generate_tournament_summary(multi_event_tournament_state)

        elif menu_choice == '15':
            # View Tournament Earnings Summary
            from woodchopping.ui.payout_ui import calculate_total_earnings, display_tournament_earnings_summary

            if not multi_event_tournament_state.get('events'):
                print("\n[WARN] No events in tournament yet")
                input("\nPress Enter to continue...")
                continue

            competitor_earnings = calculate_total_earnings(multi_event_tournament_state)

            if not competitor_earnings:
                print("\n[WARN] No payouts configured for any events")
                input("\nPress Enter to continue...")
                continue

            display_tournament_earnings_summary(multi_event_tournament_state, competitor_earnings)

        elif menu_choice == '16':
            # Save Tournament State
            if not multi_event_tournament_state.get('tournament_name'):
                print("\nERROR: Create tournament first (Option 1)")
                input("\nPress Enter to return to menu...")
                continue

            filename = input("\nEnter filename (default: saves/multi_tournament_state.json): ").strip()
            if not filename:
                filename = "saves/multi_tournament_state.json"

            save_multi_event_tournament(multi_event_tournament_state, filename)

        elif menu_choice == '17':
            # Return to main menu
            print("\nReturning to main menu...")
            break

        else:
            print("Invalid selection. Try again.")


## Championship Simulator Menu Function
def championship_simulator_menu():
    """
    Standalone menu for mock championship event simulator.

    This is a fun predictive tool that simulates championship-format races where
    all competitors start together (Mark 3) - fastest time wins. Uses existing
    prediction and Monte Carlo simulation systems to predict race outcomes.
    """
    global comp_df

    print("\n╔" + "═" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━".center(68) + "║")
    print("║" + "CHAMPIONSHIP RACE SIMULATOR".center(68) + "║")
    print("║" + "Mock Race Predictions & Analysis".center(68) + "║")
    print("║" + "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "═" * 68 + "╝")

    run_championship_simulator(comp_df)


## Main Menu - Top Level Mode Selection
''' NEW TWO-LEVEL MENU STRUCTURE (V5.0)
Top level: Choose between single event or multi-event tournament
Second level: Detailed menus for each mode
'''
while True:
    print("\n" + "╔" + "═" * 68 + "╗")
    print("║" + " " * 19 + "◆ STRATHEX MAIN MENU ◆" + " " * 27 + "║")
    print("╚" + "═" * 68 + "╝")
    print("\nMODE SELECTION:")
    print("  1. Design an Event (Single Event)")
    print("  2. Design a Tournament (Multiple Events)")
    print("\nANALYTICS:")
    print("  3. Championship Race Simulator (Fun Predictions)")
    print("  4. View Competitor Dashboard (Performance Analytics)")
    print("\nPERSONNEL & ROSTER:")
    print("  5. Add/Edit/Remove Competitors from Master Roster")
    print("\nLOAD PREVIOUS WORK:")
    print("  6. Load Previous Event/Tournament")
    print("  7. Reload Roster from Excel")
    print("\nSYSTEM:")
    print("  8. How Does This System Work? (Explanation System)")
    print("  9. Exit")
    print("=" * 70)

    menu_choice = input("\nEnter your choice (1-9): ").strip()

    if menu_choice == '1':
        # Design an Event (Single Event Mode)
        single_event_menu()

    elif menu_choice == '2':
        # Design a Tournament (Multiple Events Mode)
        multi_event_tournament_menu()

    elif menu_choice == '3':
        # Championship Race Simulator
        championship_simulator_menu()

    elif menu_choice == '4':
        # View Competitor Dashboard (Performance Analytics)
        from woodchopping.ui.competitor_dashboard import display_competitor_dashboard
        display_competitor_dashboard()

    elif menu_choice == '5':
        # Personnel management menu
        comp_df = personnel_management_menu(comp_df)

    elif menu_choice == '6':
        # Load Previous Event/Tournament
        print("\n" + "=" * 70)
        print("  LOAD PREVIOUS WORK")
        print("=" * 70)
        print("\n1. Load Single Event State")
        print("2. Load Multi-Event Tournament State")
        print("3. Cancel")

        load_choice = input("\nEnter your choice (1-3): ").strip()

        if load_choice == '1':
            # Load single event
            loaded_state = load_tournament_state("saves/tournament_state.json")
            if loaded_state:
                tournament_state.update(loaded_state)
                print("\n[OK] Single event state loaded successfully")
                input("\nPress Enter to return to menu...")
        elif load_choice == '2':
            # Load multi-event tournament
            filename = input("\nEnter filename (default: saves/multi_tournament_state.json): ").strip()
            if not filename:
                filename = "saves/multi_tournament_state.json"

            loaded_multi_state = load_multi_event_tournament(filename)
            if loaded_multi_state:
                multi_event_tournament_state.update(loaded_multi_state)
                print("\n[OK] Multi-event tournament state loaded successfully")
                input("\nPress Enter to return to menu...")
        else:
            print("\nLoad cancelled")

    elif menu_choice == '7':
        # Reload roster from Excel
        try:
            comp_df = load_competitors_df()
            print("\n[OK] Roster reloaded from Excel")
            input("\nPress Enter to return to menu...")
        except Exception as e:
            print(f"\nFailed to reload roster: {e}")
            input("\nPress Enter to return to menu...")

    elif menu_choice == '8':
        # Launch explanation system
        explain.explanation_menu()

    elif menu_choice == '9' or menu_choice == '':
        # Exit
        save_prompt = input("\nSave current work before exiting? (y/n): ").strip().lower()
        if save_prompt == 'y':
            print("\n" + "=" * 70)
            print("  SAVE OPTIONS")
            print("=" * 70)
            print("\n1. Save Single Event State")
            print("2. Save Multi-Event Tournament State")
            print("3. Skip saving")

            save_choice = input("\nEnter your choice (1-3): ").strip()

            if save_choice == '1':
                auto_save_state(tournament_state)
                print("\n[OK] Single event state saved")
            elif save_choice == '2':
                filename = input("\nEnter filename (default: saves/multi_tournament_state.json): ").strip()
                if not filename:
                    filename = "saves/multi_tournament_state.json"
                save_multi_event_tournament(multi_event_tournament_state, filename)

        print("\nGoodbye!")
        break

    else:
        print("Invalid selection. Try again.")
        input("\nPress Enter to return to menu...")
