# -*- coding: utf-8 -*-
"""Multi-event tournament management UI functions.

This module handles multi-event tournament operations including:
- Tournament creation and metadata management
- Event addition, viewing, and removal
- Batch operations across all events
- Sequential results entry workflow
- Tournament summary generation
- Multi-event state persistence
"""

import json
import copy
import sys
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import pandas as pd

# Import existing functions for reuse
from woodchopping.ui.wood_ui import wood_menu, format_wood, select_event_code
from woodchopping.ui.competitor_ui import select_all_event_competitors
from woodchopping.data import load_results_df
from woodchopping.ui.history_entry import competitor_has_event_history, prompt_add_competitor_times
from woodchopping.ui.tournament_ui import (
    calculate_tournament_scenarios,
    distribute_competitors_into_heats,
    select_heat_advancers,
    fill_advancers_with_random_draw,
    generate_next_round
)
from woodchopping.handicaps import calculate_ai_enhanced_handicaps
from woodchopping.data import load_results_df, append_results_to_excel
from woodchopping.ui.adjustment_tracking import log_handicap_adjustment
from woodchopping.ui.progress_ui import ProgressDisplay


def create_multi_event_tournament() -> Dict:
    """Create a new multi-event tournament structure.

    Prompts judge for:
    - Tournament name
    - Tournament date (optional, defaults to today)

    Returns:
        dict: Initialized multi_event_tournament_state
    """
    print(f"\n{'='*70}")
    print(f"  CREATE NEW MULTI-EVENT TOURNAMENT")
    print(f"{'='*70}")

    # Prompt for tournament name
    tournament_name = input("\nTournament name (e.g., 'Missoula Pro-Am 2026'): ").strip()
    if not tournament_name:
        tournament_name = "Unnamed Tournament"

    # Prompt for date (optional)
    date_input = input("Tournament date (YYYY-MM-DD, or press Enter for today): ").strip()
    if date_input:
        tournament_date = date_input
    else:
        tournament_date = datetime.now().strftime("%Y-%m-%d")

    # Initialize tournament state
    tournament_state = {
        'tournament_mode': 'multi_event',
        'tournament_name': tournament_name,
        'tournament_date': tournament_date,
        'created_at': datetime.now().isoformat(),
        'total_events': 0,
        'events_completed': 0,
        'current_event_index': 0,
        'events': []
    }

    print(f"\n[OK] Tournament '{tournament_name}' created for {tournament_date}")
    print(f"[OK] You can now add events to this tournament")

    return tournament_state


def setup_tournament_roster(tournament_state: Dict, comp_df: pd.DataFrame) -> Dict:
    """Setup tournament-wide competitor roster (NEW V5.1).

    Allows judge to:
    1. Select all competitors participating in tournament
    2. Enable/disable entry fee tracking (optional)

    Args:
        tournament_state: Multi-event tournament state
        comp_df: Full competitor roster DataFrame

    Returns:
        dict: Updated tournament_state with tournament_roster
    """
    # Check if roster already exists
    if tournament_state.get('tournament_roster'):
        print("\n[WARN] Tournament roster already configured")
        overwrite = input("Overwrite existing roster? (y/n): ").strip().lower()
        if overwrite != 'y':
            return tournament_state

    # Display header
    print(f"\n{'='*70}")
    print(f"  SETUP TOURNAMENT ROSTER")
    print(f"{'='*70}")
    print(f"Tournament: {tournament_state['tournament_name']}")
    print(f"Events: {tournament_state['total_events']}")

    # Entry fee tracking toggle
    print(f"\n{'='*70}")
    print(f"  ENTRY FEE TRACKING (OPTIONAL)")
    print(f"{'='*70}")
    print("\nWould you like to track entry fee payment status?")
    print("(This adds a 'Fee Paid' checkbox per competitor per event)")

    fee_tracking = input("\nEnable entry fee tracking? (y/n): ").strip().lower()
    tournament_state['entry_fee_tracking_enabled'] = (fee_tracking == 'y')

    if tournament_state['entry_fee_tracking_enabled']:
        print("\n[OK] Entry fee tracking ENABLED")
    else:
        print("\n[OK] Entry fee tracking DISABLED")

    # Select all competitors for tournament
    print(f"\n{'='*70}")
    print(f"  SELECT ALL TOURNAMENT COMPETITORS")
    print(f"{'='*70}")
    print("\nSelect ALL competitors who will compete in ANY event today.")
    print("(You'll assign specific events to each competitor in the next step)")

    # Reuse existing competitor selection UI
    from woodchopping.ui.competitor_ui import select_all_event_competitors
    selected_df = select_all_event_competitors(comp_df, max_competitors=None)

    if selected_df.empty:
        print("\n[WARN] No competitors selected. Tournament roster not configured.")
        return tournament_state

    # Build tournament roster
    roster = []
    for _, row in selected_df.iterrows():
        roster.append({
            'competitor_name': row['competitor_name'],
            'competitor_id': row.get('CompetitorID', ''),
            'events_entered': [],                # Will be populated in assignment phase
            'entry_fees_paid': {}                # Will be populated in assignment phase
        })

    tournament_state['tournament_roster'] = roster
    tournament_state['competitor_roster_df'] = selected_df

    print(f"\n{'='*70}")
    print(f"  [OK] TOURNAMENT ROSTER CONFIGURED")
    print(f"{'='*70}")
    print(f"Total competitors: {len(roster)}")
    print(f"Entry fee tracking: {'ENABLED' if tournament_state['entry_fee_tracking_enabled'] else 'DISABLED'}")
    print(f"\nNext step: Assign competitors to events")

    # Auto-save
    auto_save_multi_event(tournament_state)

    return tournament_state


def save_multi_event_tournament(tournament_state: Dict, filename: str = "saves/multi_tournament_state.json") -> None:
    """Save multi-event tournament state to JSON file.

    Handles DataFrame serialization and NumPy type conversion for all events and rounds.

    Args:
        tournament_state: Multi-event tournament state dictionary
        filename: Output filename (default: saves/multi_tournament_state.json)
    """
    import numpy as np

    class NumpyEncoder(json.JSONEncoder):
        """Custom JSON encoder for NumPy types."""
        def default(self, obj):
            if isinstance(obj, (np.integer, np.int64, np.int32)):
                return int(obj)
            elif isinstance(obj, (np.floating, np.float64, np.float32)):
                return float(obj)
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
            return super().default(obj)

    try:
        # Deep copy to avoid mutating original
        state_copy = copy.deepcopy(tournament_state)

        # Convert top-level DataFrames (V5.1)
        if 'competitor_roster_df' in state_copy and isinstance(state_copy['competitor_roster_df'], pd.DataFrame):
            state_copy['competitor_roster_df'] = state_copy['competitor_roster_df'].to_dict('records')

        # Convert DataFrames to dict records for JSON serialization
        for event in state_copy.get('events', []):
            # Convert event-level DataFrame
            if 'all_competitors_df' in event and isinstance(event['all_competitors_df'], pd.DataFrame):
                event['all_competitors_df'] = event['all_competitors_df'].to_dict('records')

            # Convert round-level DataFrames
            for round_obj in event.get('rounds', []):
                if 'competitors_df' in round_obj and isinstance(round_obj['competitors_df'], pd.DataFrame):
                    round_obj['competitors_df'] = round_obj['competitors_df'].to_dict('records')

        # Write to JSON with custom encoder for NumPy types
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(state_copy, f, indent=2, ensure_ascii=False, cls=NumpyEncoder)

        print(f"\n[OK] Tournament state saved to {filename}")

    except Exception as e:
        print(f"\n[WARN] Error saving tournament state: {e}")


def load_multi_event_tournament(filename: str = "saves/multi_tournament_state.json") -> Optional[Dict]:
    """Load multi-event tournament state from JSON file.

    Reconstructs DataFrames from dict records.

    Args:
        filename: Input filename (default: saves/multi_tournament_state.json)

    Returns:
        dict: Loaded tournament state, or None if load failed
    """
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            tournament_state = json.load(f)

        # Reconstruct top-level DataFrames (V5.1)
        if 'competitor_roster_df' in tournament_state and isinstance(tournament_state['competitor_roster_df'], list):
            tournament_state['competitor_roster_df'] = pd.DataFrame(tournament_state['competitor_roster_df'])

        # Reconstruct DataFrames
        for event in tournament_state.get('events', []):
            # Reconstruct event-level DataFrame
            if 'all_competitors_df' in event and isinstance(event['all_competitors_df'], list):
                event['all_competitors_df'] = pd.DataFrame(event['all_competitors_df'])

            # Reconstruct round-level DataFrames
            for round_obj in event.get('rounds', []):
                if 'competitors_df' in round_obj and isinstance(round_obj['competitors_df'], list):
                    round_obj['competitors_df'] = pd.DataFrame(round_obj['competitors_df'])

            # Backward compatibility: add event_type for legacy tournaments
            if 'event_type' not in event:
                event['event_type'] = 'handicap'

            # Backward compatibility: add payout_config for legacy tournaments (V4.5)
            if 'payout_config' not in event:
                event['payout_config'] = None

            # Backward compatibility: add competitor_status to events (V5.1)
            if 'competitor_status' not in event:
                event['competitor_status'] = {
                    name: 'active'
                    for name in event.get('all_competitors', [])
                }

        # Backward compatibility: add tournament_roster for legacy tournaments (V5.1)
        if 'tournament_roster' not in tournament_state:
            # Legacy tournament - build minimal roster from event assignments
            all_comp_names = set()
            for event in tournament_state.get('events', []):
                all_comp_names.update(event.get('all_competitors', []))

            # Build minimal roster
            tournament_state['tournament_roster'] = [
                {
                    'competitor_name': name,
                    'competitor_id': '',
                    'events_entered': [],  # Empty - legacy tournaments already have events populated
                    'entry_fees_paid': {}
                }
                for name in sorted(all_comp_names)
            ]
            tournament_state['entry_fee_tracking_enabled'] = False
            tournament_state['competitor_roster_df'] = pd.DataFrame()

        print(f"\n[OK] Tournament state loaded from {filename}")
        print(f"[OK] Tournament: {tournament_state.get('tournament_name', 'Unknown')}")
        print(f"[OK] Events: {tournament_state.get('total_events', 0)}")

        return tournament_state

    except FileNotFoundError:
        print(f"\n[WARN] Tournament file '{filename}' not found")
        return None
    except Exception as e:
        print(f"\n[WARN] Error loading tournament state: {e}")
        return None


def auto_save_multi_event(tournament_state: Dict) -> None:
    """Auto-save multi-event tournament state with default filename.

    Args:
        tournament_state: Multi-event tournament state dictionary
    """
    save_multi_event_tournament(tournament_state, "saves/multi_tournament_state.json")


def add_event_to_tournament(tournament_state: Dict, comp_df: pd.DataFrame, results_df: pd.DataFrame) -> Dict:
    """Add a new event to the tournament (wood, format, competitors ONLY).

    Sequential workflow:
    1. Wood characteristics (species, diameter, quality)
    2. Event code (SB/UH)
    3. Auto-generate event name (e.g., "275mm UH", "300mm SB")
    4. Tournament format (stands, heats structure)
    5. Competitor selection
    6. Set event status to 'configured' (NO HANDICAP CALCULATION)

    Handicaps will be calculated later in batch using calculate_all_event_handicaps().

    Args:
        tournament_state: Multi-event tournament state
        comp_df: Full competitor roster
        results_df: Historical results DataFrame (not used in this function anymore)

    Returns:
        dict: Updated tournament_state with new event (status: 'configured')
    """
    print(f"\n{'='*70}")
    print(f"  ADD NEW EVENT TO TOURNAMENT")
    print(f"{'='*70}")
    print(f"Tournament: {tournament_state.get('tournament_name', 'Unknown')}")
    print(f"Current events: {tournament_state.get('total_events', 0)}")
    print(f"{'='*70}")

    # Generate event ID
    event_order = tournament_state['total_events'] + 1
    event_id = f"event_{event_order}"

    # Step 1: Wood characteristics
    print(f"\n{'='*70}")
    print(f"  WOOD CONFIGURATION")
    print(f"{'='*70}")

    wood_selection = {
        "species": None,
        "size_mm": None,
        "quality": None,
        "event": None
    }

    # Reuse wood menu for species, size, quality
    wood_selection = wood_menu(wood_selection)

    # Validate wood configuration
    if not wood_selection.get('species') or not wood_selection.get('size_mm') or wood_selection.get('quality') is None:
        print("\n[WARN] Incomplete wood configuration. Cancelling event addition...")
        return tournament_state

    # Step 2: Event code (if not already set by wood menu)
    if not wood_selection.get('event'):
        wood_selection = select_event_code(wood_selection)

    # Auto-generate event name from wood configuration
    event_name = f"{int(wood_selection['size_mm'])}mm {wood_selection['event']}"
    print(f"\n[OK] Event name auto-generated: {event_name}")

    # Step 2.5: Event type selection (NEW V5.0 - includes bracket)
    print(f"\n{'='*70}")
    print(f"  EVENT TYPE FOR: {event_name}")
    print(f"{'='*70}")
    print("\n1. Handicap Event (AI-predicted marks for fair competition)")
    print("2. Championship Event (Mark 3 for all - fastest time wins)")
    print("3. Bracket Event (Head-to-head single elimination)")
    print("\nHandicap: Historical data + AI calculates individual marks for fairness")
    print("Championship: Everyone starts together (Mark 3), fastest time wins")
    print("Bracket: Single elimination head-to-head, AI-seeded, 2 stands only")

    event_type_choice = input("\nSelect event type (1, 2, or 3): ").strip()

    if event_type_choice == '1':
        event_type = 'handicap'
        print("\n[OK] Handicap event - marks will be calculated in batch later")
    elif event_type_choice == '2':
        event_type = 'championship'
        print("\n[OK] Championship event - all competitors will get Mark 3")
    elif event_type_choice == '3':
        event_type = 'bracket'
        print("\n[OK] Bracket event - single elimination tournament with AI seeding")
    else:
        print("\n[WARN] Invalid choice. Defaulting to Handicap event")
        event_type = 'handicap'

    # Step 3: Tournament format (stands + format)
    print(f"\n{'='*70}")
    print(f"  TOURNAMENT FORMAT FOR: {event_name}")
    print(f"{'='*70}")

    # BRACKET MODE: Force 2 stands, skip format selection
    if event_type == 'bracket':
        num_stands = 2
        print(f"\n[OK] Bracket mode requires exactly 2 stands (head-to-head matches)")

        try:
            tentative = int(input("Approximate number of competitors for this event: ").strip())
        except ValueError:
            print("\n[WARN] Invalid input. Cancelling event addition...")
            return tournament_state

        event_format = 'bracket'
        capacity_info = {
            'max_competitors': 999,  # No limit for brackets
            'format_description': 'Single elimination bracket'
        }

        print(f"[OK] Bracket tournament - supports any number of competitors (auto byes)")

    # REGULAR MODES: User selects stands and format
    else:
        try:
            num_stands = int(input("\nNumber of available stands for this event: ").strip())
            tentative = int(input("Approximate number of competitors for this event: ").strip())
        except ValueError:
            print("\n[WARN] Invalid input. Cancelling event addition...")
            return tournament_state

        # Calculate scenarios
        scenarios = calculate_tournament_scenarios(num_stands, tentative)

        # Display scenarios
        print(f"\n{'='*70}")
        print(f"  SCENARIO 1: Single Heat Mode")
        print(f"{'='*70}")
        print(scenarios['single_heat']['description'])

        print(f"\n{'='*70}")
        print(f"  SCENARIO 2: Heats -> Finals")
        print(f"{'='*70}")
        print(scenarios['heats_to_finals']['description'])

        print(f"\n{'='*70}")
        print(f"  SCENARIO 3: Heats -> Semis -> Finals")
        print(f"{'='*70}")
        print(scenarios['heats_to_semis_to_finals']['description'])

        # User selects format
        print(f"\n{'='*70}")
        format_choice = input("Select format (1, 2, or 3): ").strip()

        if format_choice == '1':
            event_format = 'single_heat'
            capacity_info = scenarios['single_heat']
        elif format_choice == '2':
            event_format = 'heats_to_finals'
            capacity_info = scenarios['heats_to_finals']
        elif format_choice == '3':
            event_format = 'heats_to_semis_to_finals'
            capacity_info = scenarios['heats_to_semis_to_finals']
        else:
            print("\n[WARN] Invalid choice. Cancelling event addition...")
            return tournament_state

    # Step 5: Payout configuration (OPTIONAL) - NEW V5.0
    # NOTE: Competitor selection moved to tournament-wide roster assignment (V5.1)
    print(f"\n{'='*70}")
    print(f"  PAYOUT CONFIGURATION (OPTIONAL)")
    print(f"{'='*70}")
    print("\nWould you like to configure payouts for this event?")
    print("(You can skip this if it's a non-cash event)")

    configure_payouts = input("\nConfigure payouts? (y/n): ").strip().lower()

    if configure_payouts == 'y':
        from woodchopping.ui.payout_ui import configure_event_payouts
        payout_config = configure_event_payouts()

        if payout_config:
            print(f"\n[OK] Payout configuration saved for {event_name}")
        else:
            payout_config = {'enabled': False}
            print(f"\n[OK] Payouts skipped for {event_name}")
    else:
        payout_config = {'enabled': False}
        print(f"\n[OK] Payouts skipped for {event_name}")

    # V5.1 CHANGE: All events start with 'pending' status (no competitors yet)
    # Competitors will be assigned via tournament roster workflow
    # Championship/Bracket setup deferred until after competitor assignment

    event_status = 'pending'
    handicap_results_all = []

    print(f"\n{'='*70}")
    print(f"  EVENT CONFIGURATION COMPLETE")
    print(f"{'='*70}")
    print(f"\nEvent '{event_name}' configured successfully")
    print(f"Type: {event_type.upper()}")
    print(f"Status: PENDING (competitors not yet assigned)")
    print(f"\nNext steps:")
    print(f"  1. Add all events for the tournament")
    print(f"  2. Setup tournament roster (all competitors)")
    print(f"  3. Assign competitors to events")

    # Create event object
    event_obj = {
        'event_id': event_id,
        'event_name': event_name,
        'event_order': event_order,
        'status': event_status,
        'event_type': event_type,

        # Wood characteristics
        'wood_species': wood_selection['species'],
        'wood_diameter': wood_selection['size_mm'],
        'wood_quality': wood_selection['quality'],
        'event_code': wood_selection['event'],

        # Tournament configuration
        'num_stands': num_stands,
        'format': event_format,
        'capacity_info': capacity_info,

        # Competitors (V5.1: Empty until assigned via tournament roster)
        'all_competitors': [],
        'all_competitors_df': pd.DataFrame(),
        'competitor_status': {},  # NEW V5.1: Track active/withdrawn/disqualified

        # Handicaps (empty until competitors assigned)
        'handicap_results_all': handicap_results_all,

        # Rounds (empty until competitors assigned)
        'rounds': [],

        # Final results (empty until finals complete)
        'final_results': {
            'first_place': None,
            'second_place': None,
            'third_place': None,
            'all_placements': {}
        },

        # Payout configuration (NEW V5.0)
        'payout_config': payout_config
    }

    # V5.1: Bracket-specific fields deferred until competitors assigned

    # Add event to tournament
    tournament_state['events'].append(event_obj)
    tournament_state['total_events'] += 1

    print(f"\n{'='*70}")
    print(f"  [OK] EVENT ADDED SUCCESSFULLY")
    print(f"{'='*70}")
    print(f"Event name: {event_name}")
    print(f"Event order: {event_order}")
    print(f"Event type: {event_type.upper()}")
    print(f"Wood: {wood_selection['size_mm']}mm {wood_selection['species']} (Quality {wood_selection['quality']})")
    print(f"Event code: {wood_selection['event']}")
    print(f"Format: {event_format}")
    print(f"Competitors: 0 (not yet assigned)")
    print(f"Status: PENDING (awaiting competitor assignment)")
    print(f"{'='*70}")

    # Auto-save
    auto_save_multi_event(tournament_state)

    input("\nPress Enter to continue...")

    return tournament_state


def calculate_all_event_handicaps(tournament_state: Dict, results_df: pd.DataFrame) -> Dict:
    """Calculate handicaps for ALL events in the tournament (BATCH OPERATION).

    This is the key function for the batch handicap workflow. It processes all
    configured events and calculates handicaps in one operation.

    Workflow:
    1. Validate all events are in 'configured' state
    2. For each event, calculate handicaps using calculate_ai_enhanced_handicaps()
    3. Display progress for each event
    4. Update event status to 'ready' after calculation
    5. Display final summary
    6. Auto-save tournament state

    Args:
        tournament_state: Multi-event tournament state
        results_df: Historical results DataFrame for handicap calculations

    Returns:
        dict: Updated tournament_state with handicaps calculated for all events
    """
    from woodchopping.handicaps import calculate_ai_enhanced_handicaps

    print(f"\n{'?' + '?' * 68 + '?'}")
    title = "BATCH HANDICAP CALCULATION".center(68)
    print(f"{'?'}{title}{'?'}")
    print(f"{'?' + '?' * 68 + '?'}")

    # Validation: Check all events are configured
    not_configured = [e for e in tournament_state.get('events', []) if e['status'] == 'pending']
    if not_configured:
        print(f"\n[WARN] ERROR: {len(not_configured)} event(s) not configured:")
        for event in not_configured:
            print(f"  - {event['event_name']}: {event['status']}")
        print("\nPlease configure all events before calculating handicaps.")
        input("\nPress Enter to continue...")
        return tournament_state

    # V5.1 VALIDATION: Ensure all handicap events have competitors assigned
    events_without_competitors = [
        event for event in tournament_state['events']
        if not event.get('all_competitors') and event.get('event_type') == 'handicap'
    ]

    if events_without_competitors:
        print(f"\n{'='*70}")
        print(f"  [WARN] ERROR: EVENTS WITHOUT COMPETITORS")
        print(f"{'='*70}")
        print(f"\nThe following events have no competitors assigned:")
        for event in events_without_competitors:
            print(f"  - {event['event_name']}")
        print(f"\nPlease use 'Assign Competitors to Events' first.")
        print(f"{'='*70}")
        input("\nPress Enter to continue...")
        return tournament_state

    if not tournament_state.get('events'):
        print("\n[WARN] No events to calculate handicaps for.")
        input("\nPress Enter to continue...")
        return tournament_state

    # Check if handicaps already calculated
    already_calculated = [e for e in tournament_state['events'] if e['handicap_results_all']]
    if already_calculated:
        print(f"\n[WARN] WARNING: {len(already_calculated)} event(s) already have handicaps calculated.")
        print("This will RECALCULATE handicaps for all events.")
        confirm = input("\nContinue? (y/n): ").strip().lower()
        if confirm != 'y':
            print("\n[OK] Handicap calculation cancelled")
            input("\nPress Enter to continue...")
            return tournament_state

    total_events = len(tournament_state['events'])
    total_competitors = sum(len(e['all_competitors']) for e in tournament_state['events'])
    event_label = "event" if total_events == 1 else "events"
    competitor_label = "competitor" if total_competitors == 1 else "competitors"

    print(f"\nCalculating handicaps for {total_events} {event_label} ({total_competitors} total {competitor_label})...")
    print(f"{'='*70}\n")

    # Calculate handicaps for each event
    for event_idx, event in enumerate(tournament_state['events'], 1):
        # Skip Championship events (already have Mark 3 assigned)
        if event.get('event_type') == 'championship':
            print(f"{'='*70}")
            print(f"  EVENT {event_idx} of {total_events}: {event['event_name']}")
            print(f"{'='*70}")
            print(f"[ ] Skipping Championship event (marks pre-assigned: all Mark 3)")
            print(f"{'='*70}\n")
            continue

        print(f"{'='*70}")
        print(f"  EVENT {event_idx} of {total_events}: {event['event_name']}")
        print(f"{'='*70}")
        print(f"Wood: {event['wood_diameter']}mm {event['wood_species']} (Quality {event['wood_quality']})")
        print(f"Event: {event['event_code']}")
        print(f"Competitors: {len(event['all_competitors'])}")
        print()

        progress_display = ProgressDisplay(
            title=f"HANDICAP CALCULATION - EVENT {event_idx} OF {total_events}",
            width=70,
            bar_length=40,
            item_label="competitors",
            detail_label="Analyzing"
        )
        progress_display.start()

        def show_progress(current, total, comp_name):
            """Display progress for this event"""
            progress_display.update(current, total, comp_name)

        # Calculate handicaps for this event
        handicap_results = calculate_ai_enhanced_handicaps(
            event['all_competitors_df'],
            event['wood_species'],
            event['wood_diameter'],
            event['wood_quality'],
            event['event_code'],
            results_df,
            progress_callback=show_progress
        )

        if not handicap_results:
            progress_display.finish("No handicap results returned")
            print(f"\n[WARN] Failed to calculate handicaps for {event['event_name']}")
            print("Skipping this event...")
            continue

        result_label = "competitor" if len(handicap_results) == 1 else "competitors"
        progress_display.finish(f"Completed {len(handicap_results)} {result_label}")

        # Update event with handicap results
        event['handicap_results_all'] = handicap_results
        event['status'] = 'ready'  # Now ready for heat generation

        print(f"\n[OK] Event {event_idx}: Handicaps calculated for {len(handicap_results)} {result_label}")

    # Display final summary
    print(f"{'='*70}")
    print(f"  [OK] BATCH HANDICAP CALCULATION COMPLETE")
    print(f"{'='*70}")

    calculated_events = [e for e in tournament_state['events'] if e['status'] == 'ready']
    calculated_competitors = sum(len(e['handicap_results_all']) for e in calculated_events)

    print(f"Events processed: {len(calculated_events)}/{total_events}")
    print(f"Competitors analyzed: {calculated_competitors}")
    print(f"Status: All events ready for heat generation")
    print(f"{'='*70}")

    # Auto-save
    auto_save_multi_event(tournament_state)
    print("\n[OK] Tournament state auto-saved")

    input("\nPress Enter to continue...")
    return tournament_state


def analyze_single_event(event: Dict, event_index: int, tournament_state: Dict) -> None:
    """Comprehensive handicap analysis workflow for a single event.

    Provides analysis tools:
    - Display handicap marks
    - Monte Carlo fairness simulation (optional)
    - AI prediction method analysis (optional)
    - Handicap calculation explanation (optional)

    Marks event as 'analysis_completed' when full workflow is done.

    Args:
        event: Event dict to analyze
        event_index: Index in tournament_state['events']
        tournament_state: Multi-event tournament state dict
    """
    from woodchopping.simulation import simulate_and_assess_handicaps
    from woodchopping.predictions.prediction_aggregator import (
        display_comprehensive_prediction_analysis,
        display_handicap_calculation_explanation
    )

    print(f"\n{'?' + '?' * 68 + '?'}")
    title = f"HANDICAP ANALYSIS: {event['event_name']}".center(68)
    print(f"{'?'}{title}{'?'}")
    print(f"{'?' + '?' * 68 + '?'}")

    # Validation: Check handicaps are calculated
    if event['status'] not in ['ready', 'scheduled', 'in_progress', 'completed']:
        print(f"\n[WARN] ERROR: Handicaps not calculated for this event (status: {event['status']})")
        print("\nPlease calculate handicaps first (Option 5).")
        input("\nPress Enter to continue...")
        return

    if not event['handicap_results_all']:
        print("\n[WARN] No handicaps calculated for this event.")
        input("\nPress Enter to continue...")
        return

    # Championship events: simple confirmation display (skip analysis)
    if event.get('event_type') == 'championship':
        print(f"\n{'='*70}")
        print(f"  CHAMPIONSHIP EVENT - MARK CONFIRMATION")
        print(f"{'='*70}")
        print(f"Wood: {event['wood_diameter']}mm {event['wood_species']} (Quality {event['wood_quality']})")
        print(f"Event type: {event['event_code']}")
        print(f"\n[OK] Championship Event")
        print(f"[OK] All {len(event['handicap_results_all'])} competitors have Mark 3")
        print(f"[OK] Fastest time wins - no handicap analysis needed")
        print(f"[OK] All competitors start simultaneously")
        print(f"{'='*70}")

        # Mark as analysis completed (simple approval)
        event['analysis_completed'] = True
        tournament_state['events'][event_index] = event

        input("\nPress Enter to continue...")
        return

    # PHASE 1: Display handicap marks
    print(f"\n{'='*70}")
    print(f"  HANDICAP MARKS")
    print(f"{'='*70}")
    print(f"Wood: {event['wood_diameter']}mm {event['wood_species']} (Quality {event['wood_quality']})")
    print(f"Event type: {event['event_code']}")
    print(f"{'='*70}\n")

    # Display handicaps sorted by mark
    sorted_results = sorted(event['handicap_results_all'], key=lambda x: x['mark'])

    print(f"{'Competitor':<35s} {'Predicted Time':<15s} {'Mark':<6s} {'Method'}")
    print(f"{'-'*70}")

    for result in sorted_results:
        name = result['name'][:34]
        time = f"{result['predicted_time']:.1f}s"
        mark = f"{result['mark']}"
        method = result.get('method_used', 'Unknown')[:15]

        print(f"{name:<35s} {time:<15s} {mark:<6s} {method}")

    print(f"{'-'*70}")
    print(f"Total competitors: {len(event['handicap_results_all'])}\n")

    # PHASE 2: Monte Carlo fairness simulation (optional)
    print(f"\n{'='*70}")
    run_mc = input("\nRun Monte Carlo fairness simulation? (y/n): ").strip().lower()
    if run_mc == 'y':
        print(f"\n{'?' + '?' * 68 + '?'}")
        title = f"MONTE CARLO SIMULATION".center(68)
        print(f"{'?'}{title}{'?'}")
        print(f"{'?' + '?' * 68 + '?'}\n")

        simulate_and_assess_handicaps(event['handicap_results_all'])

    # PHASE 3: AI prediction method analysis (optional)
    print(f"\n{'='*70}")
    show_ai = input("\nView detailed AI analysis of prediction methods? (y/n): ").strip().lower()
    if show_ai == 'y':
        print(f"\n{'?' + '?' * 68 + '?'}")
        title = f"AI PREDICTION ANALYSIS".center(68)
        print(f"{'?'}{title}{'?'}")
        print(f"{'?' + '?' * 68 + '?'}\n")

        # Prepare wood selection dict for this event
        wood_selection = {
            'species': event['wood_species'],
            'size_mm': event['wood_diameter'],
            'quality': event['wood_quality'],
            'event': event['event_code']
        }

        try:
            display_comprehensive_prediction_analysis(
                event['handicap_results_all'],
                wood_selection
            )
        except Exception as e:
            print(f"\n[WARN] Error during AI analysis: {e}")
            print("Continuing...")

    # PHASE 4: Explanation of handicap system (optional)
    print(f"\n{'='*70}")
    show_explanation = input("\nView explanation of how handicaps are calculated? (y/n): ").strip().lower()
    if show_explanation == 'y':
        display_handicap_calculation_explanation()

    # Mark as having completed full analysis workflow
    print(f"\n{'='*70}")
    mark_complete = input("\nMark this event's analysis as complete? (y/n): ").strip().lower()
    if mark_complete == 'y':
        event['analysis_completed'] = True
        print("\n[OK] Analysis marked as complete")
        print("  You can now manually adjust handicaps for this event in the Approval menu.")
        # Auto-save
        auto_save_multi_event(tournament_state)
        print("[OK] Tournament state auto-saved")
    else:
        print("\n[WARN] Analysis not marked complete")
        print("  Manual handicap adjustments will not be available for this event.")

    input("\nPress Enter to continue...")


def view_analyze_all_handicaps(tournament_state: Dict) -> None:
    """Event selection menu for handicap analysis.

    Allows judges to select individual events for comprehensive analysis.

    Args:
        tournament_state: Multi-event tournament state dict
    """
    while True:
        print(f"\n{'?' + '?' * 68 + '?'}")
        title = "HANDICAP ANALYSIS - EVENT SELECTION".center(68)
        print(f"{'?'}{title}{'?'}")
        print(f"{'?' + '?' * 68 + '?'}")

        # Validation: Check handicaps are calculated
        not_ready = [e for e in tournament_state.get('events', []) if e['status'] not in ['ready', 'scheduled', 'in_progress', 'completed']]
        if not_ready:
            print(f"\n[WARN] ERROR: {len(not_ready)} event(s) don't have handicaps calculated:")
            for event in not_ready:
                print(f"  - {event['event_name']}: {event['status']}")
            print("\nPlease calculate handicaps first (Option 5).")
            input("\nPress Enter to continue...")
            return

        if not tournament_state.get('events'):
            print("\n[WARN] No events in tournament.")
            input("\nPress Enter to continue...")
            return

        # Display events
        print(f"\n{'='*70}")
        print(f"  SELECT EVENT TO ANALYZE")
        print(f"{'='*70}\n")

        for idx, event in enumerate(tournament_state['events'], 1):
            status_icon = "[OK]" if event.get('analysis_completed', False) else " "
            print(f"{idx}. [{status_icon}] {event['event_name']}")
            print(f"    Wood: {event['wood_diameter']}mm {event['wood_species']} (Quality {event['wood_quality']})")
            print(f"    Competitors: {len(event.get('handicap_results_all', []))}")
            if event.get('analysis_completed', False):
                print(f"    Analysis: COMPLETED")
            else:
                print(f"    Analysis: Not completed")
            print()

        print(f"{len(tournament_state['events']) + 1}. Return to main menu")

        choice = input("\nSelect event to analyze (or return to menu): ").strip()

        if not choice.isdigit():
            print("\n[WARN] Invalid choice. Please enter a number.")
            input("\nPress Enter to continue...")
            continue

        choice_num = int(choice)

        if choice_num == len(tournament_state['events']) + 1:
            return

        if choice_num < 1 or choice_num > len(tournament_state['events']):
            print("\n[WARN] Invalid choice.")
            input("\nPress Enter to continue...")
            continue

        # Analyze selected event
        event_index = choice_num - 1
        analyze_single_event(tournament_state['events'][event_index], event_index, tournament_state)


def approve_event_handicaps(tournament_state: Dict) -> None:
    """Event selection menu for handicap approval.

    Allows judges to approve handicaps event-by-event.
    Manual adjustments require full analysis to have been completed.

    Args:
        tournament_state: Multi-event tournament state dict
    """
    from woodchopping.ui.handicap_ui import judge_approval

    while True:
        print(f"\n{'?' + '?' * 68 + '?'}")
        title = "HANDICAP APPROVAL - EVENT SELECTION".center(68)
        print(f"{'?'}{title}{'?'}")
        print(f"{'?' + '?' * 68 + '?'}")

        # Validation: Check handicaps are calculated
        not_ready = [e for e in tournament_state.get('events', []) if e['status'] not in ['ready', 'scheduled', 'in_progress', 'completed']]
        if not_ready:
            print(f"\n[WARN] ERROR: {len(not_ready)} event(s) don't have handicaps calculated:")
            for event in not_ready:
                print(f"  - {event['event_name']}: {event['status']}")
            print("\nPlease calculate handicaps first (Option 5).")
            input("\nPress Enter to continue...")
            return

        if not tournament_state.get('events'):
            print("\n[WARN] No events in tournament.")
            input("\nPress Enter to continue...")
            return

        # Display events
        print(f"\n{'='*70}")
        print(f"  SELECT EVENT TO APPROVE")
        print(f"{'='*70}\n")

        for idx, event in enumerate(tournament_state['events'], 1):
            approved = all(r.get('approved_by') for r in event.get('handicap_results_all', []))
            analysis_done = event.get('analysis_completed', False)

            if approved:
                status_icon = "[OK]"
                status_text = "APPROVED"
            else:
                status_icon = " "
                status_text = "Not approved"

            print(f"{idx}. [{status_icon}] {event['event_name']}")
            print(f"    Wood: {event['wood_diameter']}mm {event['wood_species']} (Quality {event['wood_quality']})")
            print(f"    Competitors: {len(event.get('handicap_results_all', []))}")
            print(f"    Status: {status_text}")
            print(f"    Analysis: {'COMPLETED' if analysis_done else 'Not completed (manual adjustments unavailable)'}")
            print()

        print(f"{len(tournament_state['events']) + 1}. Approve ALL events at once")
        print(f"{len(tournament_state['events']) + 2}. Return to main menu")

        choice = input("\nSelect event to approve (or choose option): ").strip()

        if not choice.isdigit():
            print("\n[WARN] Invalid choice. Please enter a number.")
            input("\nPress Enter to continue...")
            continue

        choice_num = int(choice)

        # Return to menu
        if choice_num == len(tournament_state['events']) + 2:
            return

        # Approve all events
        if choice_num == len(tournament_state['events']) + 1:
            print(f"\n{'='*70}")
            print(f"  APPROVE ALL EVENTS")
            print(f"{'='*70}")

            confirm = input("\nApprove handicaps for ALL events? (y/n): ").strip().lower()
            if confirm == 'y':
                initials, timestamp = judge_approval()

                if initials:
                    # Mark all events as approved
                    for event in tournament_state['events']:
                        if event['handicap_results_all']:
                            for result in event['handicap_results_all']:
                                result['approved_by'] = initials
                                result['approved_at'] = timestamp

                    print(f"\n[OK] All handicaps approved by {initials} at {timestamp}")
                    # Auto-save
                    auto_save_multi_event(tournament_state)
                    print("[OK] Tournament state auto-saved")
                else:
                    print("\n[WARN] Approval cancelled")

            input("\nPress Enter to continue...")
            continue

        # Individual event approval
        if choice_num < 1 or choice_num > len(tournament_state['events']):
            print("\n[WARN] Invalid choice.")
            input("\nPress Enter to continue...")
            continue

        event_index = choice_num - 1
        event = tournament_state['events'][event_index]

        # Show approval menu for this event
        print(f"\n{'?' + '?' * 68 + '?'}")
        title = f"APPROVE: {event['event_name']}".center(68)
        print(f"{'?'}{title}{'?'}")
        print(f"{'?' + '?' * 68 + '?'}")

        if not event['handicap_results_all']:
            print("\n[WARN] No handicaps calculated for this event.")
            input("\nPress Enter to continue...")
            continue

        # Check if already approved
        already_approved = all(r.get('approved_by') for r in event['handicap_results_all'])
        if already_approved:
            approver = event['handicap_results_all'][0].get('approved_by', 'Unknown')
            approved_time = event['handicap_results_all'][0].get('approved_at', 'Unknown')
            print(f"\n[OK] This event was already approved by {approver} at {approved_time}")

            reapprove = input("\nRe-approve these handicaps? (y/n): ").strip().lower()
            if reapprove != 'y':
                input("\nPress Enter to continue...")
                continue

        # Show handicaps
        print(f"\n{'='*70}")
        print(f"  HANDICAP MARKS")
        print(f"{'='*70}\n")

        sorted_results = sorted(event['handicap_results_all'], key=lambda x: x['mark'])

        print(f"{'Competitor':<35s} {'Predicted Time':<15s} {'Mark':<6s}")
        print(f"{'-'*70}")

        for result in sorted_results:
            name = result['name'][:34]
            time = f"{result['predicted_time']:.1f}s"
            mark = f"{result['mark']}"

            print(f"{name:<35s} {time:<15s} {mark:<6s}")

        print(f"{'-'*70}")
        print(f"Total competitors: {len(event['handicap_results_all'])}\n")

        # Championship events: simplified approval (no manual adjustments)
        if event.get('event_type') == 'championship':
            print(f"\n{'='*70}")
            print(f"  CHAMPIONSHIP EVENT APPROVAL")
            print(f"{'='*70}")
            print("\nChampionship Event - all competitors have Mark 3")
            print("No manual adjustments available (all marks are identical)")
            print("\n1. Approve marks as assigned")
            print("2. Cancel (return to event selection)")

            approval_choice = input("\nYour choice (1-2): ").strip()

            if approval_choice == '1':
                # Accept championship marks
                initials, timestamp = judge_approval()

                if initials:
                    # Mark this event as approved
                    for result in event['handicap_results_all']:
                        result['approved_by'] = initials
                        result['approved_at'] = timestamp

                    print(f"\n[OK] Championship marks approved by {initials} at {timestamp}")
                    # Auto-save
                    auto_save_multi_event(tournament_state)
                    print("[OK] Tournament state auto-saved")
                else:
                    print("\n[WARN] Approval cancelled")

                input("\nPress Enter to continue...")
            else:
                # Cancel - return to event selection
                continue

            # Skip the rest of the approval flow for Championship events
            continue

        # Handicap events: full approval options
        # Approval options
        print(f"\n{'='*70}")
        print(f"  APPROVAL OPTIONS")
        print(f"{'='*70}")
        print("\n1. Accept handicaps as calculated")
        print("2. Manually adjust handicaps")
        print("3. Cancel (return to event selection)")

        approval_choice = input("\nYour choice (1-3): ").strip()

        if approval_choice == '1':
            # Accept handicaps
            initials, timestamp = judge_approval()

            if initials:
                # Mark this event as approved
                for result in event['handicap_results_all']:
                    result['approved_by'] = initials
                    result['approved_at'] = timestamp

                print(f"\n[OK] Handicaps approved by {initials} at {timestamp}")
                # Auto-save
                auto_save_multi_event(tournament_state)
                print("[OK] Tournament state auto-saved")
            else:
                print("\n[WARN] Approval cancelled")

            input("\nPress Enter to continue...")

        elif approval_choice == '2':
            # Check if analysis was completed
            if not event.get('analysis_completed', False):
                print(f"\n{'='*70}")
                print(f"  [WARN] ANALYSIS REQUIRED FOR MANUAL ADJUSTMENTS")
                print(f"{'='*70}")
                print("\nManual adjustments require full analysis to be completed first.")
                print("This ensures you understand the handicap calculations and fairness metrics")
                print("before making changes.")
                print("\nPlease:")
                print("1. Return to main menu")
                print("2. Select Option 6 (Analyze Handicaps)")
                print("3. Run full analysis for this event (marks, Monte Carlo, AI analysis)")
                print("4. Mark analysis as complete")
                print("5. Return here to make manual adjustments")
                input("\nPress Enter to continue...")
                continue

            # Manual adjustment workflow
            print(f"\n{'='*70}")
            print(f"  MANUAL HANDICAP ADJUSTMENT")
            print(f"{'='*70}")
            print("\n[WARN] This feature allows you to override calculated handicaps.")
            print("Use this ONLY if you have specific knowledge about:")
            print("  - Recent injuries or form changes")
            print("  - Equipment issues")
            print("  - Other factors not reflected in historical data")

            confirm = input("\nProceed with manual adjustments? (y/n): ").strip().lower()
            if confirm != 'y':
                print("\n[WARN] Manual adjustment cancelled")
                input("\nPress Enter to continue...")
                continue

            # Allow manual mark adjustment
            print("\nEnter competitor name to adjust (or 'done' to finish):")
            while True:
                comp_name = input("\nCompetitor name: ").strip()

                if comp_name.lower() == 'done':
                    break

                # Find competitor
                matching = [r for r in event['handicap_results_all'] if comp_name.lower() in r['name'].lower()]

                if not matching:
                    print(f"\n[WARN] No competitor found matching '{comp_name}'")
                    continue

                if len(matching) > 1:
                    print(f"\n[WARN] Multiple matches found:")
                    for r in matching:
                        print(f"  - {r['name']}")
                    print("Please be more specific.")
                    continue

                result = matching[0]
                print(f"\nCompetitor: {result['name']}")
                print(f"Current mark: {result['mark']}")
                print(f"Predicted time: {result['predicted_time']:.1f}s")

                new_mark = input("\nEnter new mark (or blank to cancel): ").strip()

                if not new_mark:
                    print("[WARN] No change made")
                    continue

                if not new_mark.isdigit() or int(new_mark) < 3:
                    print("[WARN] Invalid mark. Must be >= 3.")
                    continue

                # A5: Prompt for reason
                print("\n" + "-" * 70)
                print("Please explain why you're adjusting this handicap (for audit trail):")
                reason = input("Reason: ").strip()
                while not reason:
                    print("[WARN] Reason is required for adjustment tracking.")
                    reason = input("Reason: ").strip()

                old_mark = result['mark']
                result['mark'] = int(new_mark)
                result['manually_adjusted'] = True
                result['original_mark'] = old_mark
                result['adjustment_reason'] = reason  # A5: Store reason

                print(f"\n[OK] Mark changed from {old_mark} to {new_mark}")
                print(f"  Reason: {reason}")

            # After adjustments, require approval
            print(f"\n{'='*70}")
            print(f"  APPROVE ADJUSTED HANDICAPS")
            print(f"{'='*70}")

            initials, timestamp = judge_approval()

            if initials:
                # A5: Log all manual adjustments to event state
                for result in event['handicap_results_all']:
                    if result.get('manually_adjusted'):
                        log_handicap_adjustment(
                            tournament_state=event,  # Log to event state (part of multi-event tournament)
                            competitor_name=result['name'],
                            original_mark=result.get('original_mark', result['mark']),
                            adjusted_mark=result['mark'],
                            reason=result.get('adjustment_reason', 'No reason provided'),
                            adjustment_type='manual'
                        )

                # Mark this event as approved
                for result in event['handicap_results_all']:
                    result['approved_by'] = initials
                    result['approved_at'] = timestamp

                print(f"\n[OK] Adjusted handicaps approved by {initials} at {timestamp}")
                # Auto-save
                auto_save_multi_event(tournament_state)
                print("[OK] Tournament state auto-saved")
            else:
                print("\n[WARN] Approval cancelled - adjustments saved but not approved")

            input("\nPress Enter to continue...")

        # Choice 3 just returns to event selection (loop continues)


def view_wood_count(tournament_state: Dict) -> None:
    """Display wood requirements breakdown for tournament.

    Shows:
    - Per-event wood requirements (species, diameter, count, event type)
    - Grand total by species (with full species names)
    - Overall grand total blocks needed

    Args:
        tournament_state: Multi-event tournament state
    """
    from collections import defaultdict
    from woodchopping.data.excel_io import get_species_name_from_code

    print(f"\n{'?' + '?' * 68 + '?'}")
    title = f"WOOD COUNT: {tournament_state.get('tournament_name', 'Unknown')}".center(68)
    print(f"{'?'}{title}{'?'}")
    print(f"{'?' + '?' * 68 + '?'}")

    if not tournament_state.get('events'):
        print("\n[WARN] No events added yet. Use 'Add Event to Tournament' to begin.")
        input("\nPress Enter to continue...")
        return

    # Collect wood requirements per event
    print(f"\n{'='*70}")
    print(f"  WOOD REQUIREMENTS BY EVENT")
    print(f"{'='*70}\n")
    print(f"{'Event':<30s} {'Species':<20s} {'Diameter':<10s} {'Blocks':<10s}")
    print(f"{'-'*70}")

    species_totals = defaultdict(int)
    size_species_totals = defaultdict(int)  # Track size/species combinations
    grand_total = 0

    for event in tournament_state['events']:
        # Get event type indicator
        event_type = event.get('event_type', 'handicap')
        type_indicator = 'CHMP' if event_type == 'championship' else 'HC'

        # Format event name with type indicator
        event_name_raw = event['event_name'][:24]
        event_name = f"{event_name_raw} ({type_indicator})"[:29]

        # Convert species code to full name
        species_code = event['wood_species']
        species_name = get_species_name_from_code(species_code)[:19]
        diameter = f"{int(event['wood_diameter'])}mm"
        blocks = event['capacity_info'].get('total_blocks', 0)

        print(f"{event_name:<30s} {species_name:<20s} {diameter:<10s} {blocks:<10d}")

        # Track totals by species code (for species total section)
        species_totals[species_code] += blocks

        # Track totals by size/species combination (diameter_mm, species_code)
        size_species_key = (int(event['wood_diameter']), species_code)
        size_species_totals[size_species_key] += blocks

        grand_total += blocks

    print(f"{'-'*70}")

    # Breakdown by size/species combination
    print(f"\n{'='*70}")
    print(f"  BREAKDOWN BY SIZE & SPECIES")
    print(f"{'='*70}\n")
    print(f"{'Size/Species':<50s} {'Blocks':<10s}")
    print(f"{'-'*70}")

    # Sort by diameter first, then by species name
    sorted_size_species = sorted(size_species_totals.items(), key=lambda x: (x[0][0], get_species_name_from_code(x[0][1])))

    for (diameter, species_code), blocks in sorted_size_species:
        species_name = get_species_name_from_code(species_code)
        size_species_label = f"{diameter}mm {species_name}"
        print(f"{size_species_label:<50s} {blocks:<10d}")

    print(f"{'-'*70}")

    # Grand total by species (with full names)
    print(f"\n{'='*70}")
    print(f"  GRAND TOTAL BY SPECIES")
    print(f"{'='*70}\n")
    print(f"{'Species':<40s} {'Total Blocks':<10s}")
    print(f"{'-'*70}")

    for species_code in sorted(species_totals.keys(), key=lambda x: get_species_name_from_code(x)):
        # Convert species code to full name
        species_name = get_species_name_from_code(species_code)
        print(f"{species_name:<40s} {species_totals[species_code]:<10d}")

    print(f"{'-'*70}")

    # Overall grand total
    print(f"\n{'='*70}")
    print(f"  OVERALL GRAND TOTAL")
    print(f"{'='*70}")
    print(f"\nTotal blocks needed: {grand_total}")
    print(f"{'='*70}")

    input("\nPress Enter to continue...")


def view_tournament_schedule(tournament_state: Dict) -> None:
    """Display complete tournament schedule for all events.

    Shows:
    - Event order and names
    - Wood configurations
    - Competitor counts
    - Format details (heats, semis, finals)
    - Total blocks needed per event
    - Overall tournament summary

    Args:
        tournament_state: Multi-event tournament state
    """
    print(f"\n{'?' + '?' * 68 + '?'}")
    title = f"TOURNAMENT SCHEDULE: {tournament_state.get('tournament_name', 'Unknown')}".center(68)
    print(f"{'?'}{title}{'?'}")
    print(f"{'?' + '?' * 68 + '?'}")

    print(f"\nDate: {tournament_state.get('tournament_date', 'Unknown')}")
    print(f"Total events: {tournament_state.get('total_events', 0)}")
    print(f"Events completed: {tournament_state.get('events_completed', 0)}")

    if not tournament_state.get('events'):
        print("\n[WARN] No events added yet. Use 'Add Event to Tournament' to begin.")
        input("\nPress Enter to continue...")
        return

    # Display each event
    for event in tournament_state['events']:
        print(f"\n{'='*70}")
        print(f"  EVENT {event['event_order']}: {event['event_name']}")
        print(f"{'='*70}")
        print(f"Status: {event['status'].upper()}")
        print(f"Wood: {event['wood_diameter']}mm {event['wood_species']} (Quality {event['wood_quality']})")
        print(f"Event type: {event['event_code']}")
        print(f"Stands: {event['num_stands']}")
        print(f"Format: {event['format']}")
        print(f"Competitors: {len(event['all_competitors'])}")
        print(f"Handicaps: {'Calculated' if event['handicap_results_all'] else 'Not calculated'}")

        # Show capacity info
        capacity = event['capacity_info']
        print(f"\nFormat details:")
        print(f"  - Heats: {capacity.get('num_heats', 0)}")
        if capacity.get('num_semis', 0) > 0:
            print(f"  - Semi-finals: {capacity.get('num_semis', 0)}")
        if capacity.get('num_finals', 0) > 0:
            print(f"  - Finals: {capacity.get('num_finals', 0)}")
        print(f"  - Total blocks needed: {capacity.get('total_blocks', 0)}")

        # Show rounds if generated
        if event['rounds']:
            print(f"\nRounds generated: {len(event['rounds'])}")
            for round_obj in event['rounds']:
                status_icon = "[OK]" if round_obj['status'] == 'completed' else "[ ]" if round_obj['status'] == 'pending' else "[WARN]"
                print(f"  {status_icon} {round_obj['round_name']}: {len(round_obj['competitors'])} competitors ({round_obj['status']})")

    # Overall summary
    print(f"\n{'='*70}")
    print(f"  TOURNAMENT SUMMARY")
    print(f"{'='*70}")

    total_competitors = sum(len(event['all_competitors']) for event in tournament_state['events'])
    total_blocks = sum(event['capacity_info'].get('total_blocks', 0) for event in tournament_state['events'])

    print(f"Total unique competitors: {total_competitors} (may include duplicates across events)")
    print(f"Total blocks needed: {total_blocks}")

    input("\nPress Enter to continue...")


def remove_event_from_tournament(tournament_state: Dict) -> Dict:
    """Remove an event from tournament with confirmation.

    Prompts judge to select event to remove, confirms deletion,
    and reorders remaining events.

    Args:
        tournament_state: Multi-event tournament state

    Returns:
        dict: Updated tournament_state
    """
    if not tournament_state.get('events'):
        print("\n[WARN] No events to remove.")
        input("\nPress Enter to continue...")
        return tournament_state

    print(f"\n{'='*70}")
    print(f"  REMOVE EVENT FROM TOURNAMENT")
    print(f"{'='*70}")

    # Display events
    for i, event in enumerate(tournament_state['events'], 1):
        status_warning = ""
        if event['rounds']:
            completed = sum(1 for r in event['rounds'] if r['status'] == 'completed')
            total = len(event['rounds'])
            if completed > 0:
                status_warning = f" [[WARN] HAS RESULTS: {completed}/{total} rounds complete]"

        print(f"  {i}) {event['event_name']} ({event['status']}){status_warning}")

    print(f"\n  0) Cancel")

    # Get selection
    try:
        choice = int(input("\nSelect event to remove (number): ").strip())
        if choice == 0:
            print("Cancelling...")
            return tournament_state

        if choice < 1 or choice > len(tournament_state['events']):
            print("[WARN] Invalid selection.")
            input("\nPress Enter to continue...")
            return tournament_state

        event_to_remove = tournament_state['events'][choice - 1]

        # Confirm deletion
        print(f"\n[WARN] WARNING: You are about to remove:")
        print(f"  Event: {event_to_remove['event_name']}")
        print(f"  Status: {event_to_remove['status']}")

        if event_to_remove['rounds']:
            completed = sum(1 for r in event_to_remove['rounds'] if r['status'] == 'completed')
            if completed > 0:
                print(f"  [WARN][WARN] This event has {completed} completed round(s) with recorded results!")

        confirm = input("\nType 'DELETE' to confirm removal: ").strip()

        if confirm != 'DELETE':
            print("Cancelling...")
            return tournament_state

        # Remove event
        tournament_state['events'].pop(choice - 1)
        tournament_state['total_events'] -= 1

        # Reorder remaining events
        for i, event in enumerate(tournament_state['events'], 1):
            event['event_order'] = i
            event['event_id'] = f"event_{i}"

        print(f"\n[OK] Event '{event_to_remove['event_name']}' removed successfully")
        print(f"[OK] Remaining events reordered")

        # Auto-save
        auto_save_multi_event(tournament_state)

    except ValueError:
        print("[WARN] Invalid input.")

    input("\nPress Enter to continue...")
    return tournament_state


def assign_competitors_to_events(tournament_state: Dict) -> Dict:
    """Assign each competitor to their events (competitor-by-competitor workflow) (NEW V5.1).

    Workflow:
    1. For each competitor in tournament_roster:
       - Display all available events
       - Allow multi-select which events they compete in
       - Optionally track entry fee payment per event
    2. Auto-save after completion
    3. Populate event.all_competitors from assignments

    Args:
        tournament_state: Multi-event tournament state with tournament_roster

    Returns:
        dict: Updated tournament_state with event assignments complete
    """
    # Validation
    if not tournament_state.get('tournament_roster'):
        print("\n[WARN] ERROR: Tournament roster not configured.")
        print("Please use 'Setup Tournament Roster' first.")
        input("\nPress Enter to continue...")
        return tournament_state

    if not tournament_state.get('events'):
        print("\n[WARN] ERROR: No events configured.")
        print("Please add events first.")
        input("\nPress Enter to continue...")
        return tournament_state

    roster = tournament_state['tournament_roster']
    events = tournament_state['events']
    fee_tracking = tournament_state.get('entry_fee_tracking_enabled', False)

    print(f"\n{'='*70}")
    print(f"  ASSIGN COMPETITORS TO EVENTS")
    print(f"{'='*70}")
    print(f"Tournament: {tournament_state['tournament_name']}")
    print(f"Total competitors: {len(roster)}")
    print(f"Total events: {len(events)}")
    print(f"\nYou'll now assign each competitor to their events.")
    print(f"{'='*70}")

    # Display all events for reference
    print(f"\n{'='*70}")
    print(f"  AVAILABLE EVENTS")
    print(f"{'='*70}")
    for i, event in enumerate(events, 1):
        print(f"{i}. {event['event_name']} ({event['event_type'].upper()})")
        print(f"   Wood: {event['wood_diameter']}mm {event['wood_species']} (Q{event['wood_quality']})")
    print(f"{'='*70}")

    input("\nPress Enter to begin competitor assignment...")

    # Process each competitor
    for comp_idx, comp in enumerate(roster, 1):
        comp_name = comp['competitor_name']

        print(f"\n{'='*70}")
        print(f"  COMPETITOR {comp_idx}/{len(roster)}: {comp_name}")
        print(f"{'='*70}")

        # Show current assignments if any
        if comp['events_entered']:
            print(f"\nCurrent assignments:")
            for event_id in comp['events_entered']:
                event = next((e for e in events if e['event_id'] == event_id), None)
                if event:
                    print(f"  - {event['event_name']}")
        else:
            print(f"\nNo events assigned yet.")

        # Display event options
        print(f"\nSelect which events {comp_name} will compete in:")
        for i, event in enumerate(events, 1):
            print(f"{i}. {event['event_name']}")

        print(f"\nEnter event numbers separated by commas (e.g., '1,3,5')")
        print(f"Or enter 'skip' to skip this competitor")
        print(f"Or enter 'quit' to exit assignment (progress will be saved)")

        selection = input("\nEvent numbers: ").strip().lower()

        if selection == 'quit':
            print(f"\n[WARN] Exiting assignment. Progress saved.")
            break

        if selection == 'skip':
            print(f"[WARN] Skipped {comp_name}")
            continue

        # Parse selection
        try:
            event_indices = [int(x.strip()) - 1 for x in selection.split(',')]
            selected_events = [events[i] for i in event_indices if 0 <= i < len(events)]
        except (ValueError, IndexError):
            print(f"[WARN] Invalid input. Skipping {comp_name}")
            continue

        if not selected_events:
            print(f"[WARN] No valid events selected. Skipping {comp_name}")
            continue

        # Validate history per event with N>=3 minimum requirement
        from woodchopping.data.validation import check_competitor_eligibility
        results_df = load_results_df()
        final_events = []
        blocked_events = []
        warned_events = []

        for event in selected_events:
            # CRITICAL: Use 'event_code' (SB/UH), NOT 'event_type' (handicap/championship)
            event_code = str(event.get('event_code', '')).strip().upper()
            if not event_code:
                final_events.append(event)
                continue

            # Check eligibility with NEW sparse data validation (N>=3)
            is_eligible, message, count = check_competitor_eligibility(results_df, comp_name, event_code)

            if is_eligible and not message:
                # Has sufficient history (N >= 10)
                final_events.append(event)
                continue
            elif is_eligible and message:
                # Has minimum history (3 <= N < 10) - LOW confidence warning
                warned_events.append((event, count))
                final_events.append(event)
                continue
            else:
                # BLOCKED - insufficient history (N < 3)
                blocked_events.append(event)
                print(f"\nBLOCKED: {comp_name} has only {count} {event_code} results")
                print(f"  Absolute minimum: 3 results required")
                add_now = input("Add times now to make them eligible? (y/n): ").strip().lower()
                if add_now == 'y':
                    added = prompt_add_competitor_times(comp_name, event_code, {
                        'species': event.get('wood_species'),
                        'size_mm': event.get('wood_diameter'),
                        'quality': event.get('wood_quality')
                    })
                    if added:
                        results_df = load_results_df()
                        is_eligible, message, count = check_competitor_eligibility(results_df, comp_name, event_code)
                        if is_eligible:
                            final_events.append(event)
                            if message:  # Still has warning
                                warned_events.append((event, count))
                            continue

                print(f"Skipping {comp_name} for {event.get('event_name')} (insufficient history).")

        # Display warnings for low-confidence events
        if warned_events:
            print(f"\n{'='*70}")
            print(f"  WARNING: Low Confidence Predictions")
            print(f"{'='*70}")
            for event, count in warned_events:
                print(f"  ! {event['event_name']} - Only {count} results")
            print(f"\n  Predictions will be less reliable (expect 5-10s error).")
            print(f"{'='*70}")
            input("\nPress Enter to continue...")

        if not final_events:
            print(f"WARNING: No eligible events selected for {comp_name}.")
            continue

        # Update competitor assignments
        comp['events_entered'] = [e['event_id'] for e in final_events]

        # Entry fee tracking (if enabled)
        if fee_tracking:
            print(f"\n{'='*70}")
            print(f"  ENTRY FEE TRACKING")
            print(f"{'='*70}")

            for event in final_events:
                event_name = event['event_name']

                # Check if already tracked
                current_status = comp['entry_fees_paid'].get(event['event_id'], False)
                status_str = "PAID" if current_status else "UNPAID"

                fee_paid = input(f"{event_name} - Fee paid? (y/n, currently {status_str}): ").strip().lower()
                comp['entry_fees_paid'][event['event_id']] = (fee_paid == 'y')

        print(f"\n[OK] {comp_name} assigned to {len(selected_events)} event(s)")

    # Populate event.all_competitors from assignments
    print(f"\n{'='*70}")
    print(f"  POPULATING EVENT ROSTERS")
    print(f"{'='*70}")

    comp_roster_df = tournament_state.get('competitor_roster_df')

    for event in events:
        # Find all competitors assigned to this event
        assigned_comps = [
            comp['competitor_name']
            for comp in roster
            if event['event_id'] in comp['events_entered']
        ]

        # Update event
        event['all_competitors'] = assigned_comps

        # Create DataFrame subset
        if comp_roster_df is not None and not comp_roster_df.empty:
            event['all_competitors_df'] = comp_roster_df[
                comp_roster_df['competitor_name'].isin(assigned_comps)
            ].copy()
        else:
            event['all_competitors_df'] = pd.DataFrame()

        # Initialize competitor status
        event['competitor_status'] = {name: 'active' for name in assigned_comps}

        # Update event status
        if assigned_comps:
            # Event now has competitors - can move to 'configured'
            if event['status'] == 'pending':
                event['status'] = 'configured'

        print(f"  {event['event_name']}: {len(assigned_comps)} competitors")

    print(f"\n{'='*70}")
    print(f"  [OK] COMPETITOR ASSIGNMENT COMPLETE")
    print(f"{'='*70}")

    # Auto-save
    auto_save_multi_event(tournament_state)

    input("\nPress Enter to continue...")

    return tournament_state


def generate_complete_day_schedule(tournament_state: Dict) -> Dict:
    """Generate initial heats for ALL events in tournament.

    For each event:
    - Generate heats using snake draft distribution
    - Update event status to 'scheduled'
    - Display heat assignments

    IMPORTANT: All events must have handicaps calculated first (status='ready').
    Use 'Calculate Handicaps for All Events' before generating schedule.

    Args:
        tournament_state: Multi-event tournament state

    Returns:
        dict: Updated tournament_state with heats generated for all events
    """
    print(f"\n{'?' + '?' * 68 + '?'}")
    title = f"GENERATE COMPLETE DAY SCHEDULE".center(68)
    print(f"{'?'}{title}{'?'}")
    print(f"{'?' + '?' * 68 + '?'}")

    # Validation: All events must have handicaps calculated (status='ready')
    not_ready = [e for e in tournament_state.get('events', []) if e['status'] != 'ready']
    if not_ready:
        print(f"\n[WARN] ERROR: {len(not_ready)} event(s) do not have handicaps calculated:")
        for event in not_ready:
            status_msg = "handicaps NOT calculated" if event['status'] == 'configured' else event['status']
            print(f"  - {event['event_name']}: {status_msg}")
        print("\n[WARN] Please calculate handicaps for ALL events first (use Option 5).")
        print("   Workflow: Configure events -> Calculate handicaps -> Generate schedule")
        input("\nPress Enter to continue...")
        return tournament_state

    if not tournament_state.get('events'):
        print("\n[WARN] No events to generate schedule for.")
        input("\nPress Enter to continue...")
        return tournament_state

    # Generate heats for each event
    for event in tournament_state['events']:
        # Get event type indicator
        event_type = event.get('event_type', 'handicap')
        type_indicator = '(CHMP)' if event_type == 'championship' else '(HCP)'
        event_display_name = f"{event['event_name']} {type_indicator}"

        # Skip if already generated
        if event['rounds']:
            print(f"\n[ ] {event_display_name}: Heats already generated (skipping)")
            continue

        # Display prominent event banner
        print("\n" + "╔" + "═" * 68 + "╗")
        print("║" + event_display_name.center(68) + "║")
        print("╚" + "═" * 68 + "╝")

        num_competitors = len(event['all_competitors'])
        num_stands = event['num_stands']

        # Check format
        if event['format'] == 'single_heat':
            # Single heat mode
            heats = [{
                'round_name': 'Heat 1',
                'round_type': 'heat',
                'round_number': 1,
                'competitors': event['all_competitors'],
                'competitors_df': event['all_competitors_df'],
                'handicap_results': event['handicap_results_all'],
                'num_to_advance': 0,
                'status': 'pending',
                'actual_results': {},
                'finish_order': {},
                'advancers': []
            }]

            # Display detailed stand assignments
            print(f"\n{'-'*70}")
            print(f"  Heat 1 - Single Heat Mode")
            print(f"{'-'*70}")

            # Display competitors with stand numbers and marks
            for stand_num, comp_name in enumerate(heats[0]['competitors'], 1):
                # Find handicap mark for this competitor
                mark = next((c['mark'] for c in heats[0]['handicap_results'] if c['name'] == comp_name), '?')
                mark_str = str(mark) if isinstance(mark, int) else mark

                # Label backmarker and frontmarker (only for handicap events)
                if event_type == 'championship':
                    label = ""
                elif stand_num == 1:
                    label = " ? Backmarker"
                elif stand_num == len(heats[0]['competitors']):
                    label = " ? Frontmarker"
                else:
                    label = ""

                print(f"  Stand {stand_num:2d}: {comp_name:35s} Mark {mark_str:3s}{label}")

            print(f"{'-'*70}")

        else:
            # Multi-round tournament mode
            # Use optimal stands_per_heat from capacity calculation (may be less than total num_stands)
            from math import ceil
            capacity_info = event.get('capacity_info', {})
            stands_per_heat = capacity_info.get('stands_per_heat', num_stands)  # Fallback to num_stands for old saved states
            num_heats = capacity_info.get('num_heats', ceil(num_competitors / num_stands))

            heats = distribute_competitors_into_heats(
                event['all_competitors_df'],
                event['handicap_results_all'],
                stands_per_heat,  # Use optimal stands per heat, not total available stands
                num_heats
            )

            # Display detailed heat assignments with stand numbers
            for heat in heats:
                print(f"\n{'-'*70}")
                print(f"  {heat['round_name']} - {len(heat['competitors'])} competitors (top {heat['num_to_advance']} advance)")
                print(f"{'-'*70}")

                # Competitors are already sorted by snake draft (backmarker first, frontmarker last)
                for stand_num, comp_name in enumerate(heat['competitors'], 1):
                    # Find handicap mark for this competitor
                    mark = next((c['mark'] for c in heat['handicap_results'] if c['name'] == comp_name), '?')
                    mark_str = str(mark) if isinstance(mark, int) else mark

                    # Label backmarker and frontmarker (only for handicap events)
                    if event_type == 'championship':
                        label = ""
                    elif stand_num == 1:
                        label = " ? Backmarker"
                    elif stand_num == len(heat['competitors']):
                        label = " ? Frontmarker"
                    else:
                        label = ""

                    print(f"  Stand {stand_num:2d}: {comp_name:35s} Mark {mark_str:3s}{label}")

                print(f"{'-'*70}")

        # Update event
        event['rounds'] = heats
        event['status'] = 'scheduled'  # Heats generated, ready for competition

        print(f"[OK] {event_display_name}: Heats generated successfully")

    print(f"\n{'='*70}")
    print(f"  [OK] COMPLETE DAY SCHEDULE GENERATED")
    print(f"{'='*70}")
    print(f"All events ready for competition!")

    # Auto-save
    auto_save_multi_event(tournament_state)

    input("\nPress Enter to continue...")
    return tournament_state


def view_all_handicaps_summary(tournament_state: Dict) -> None:
    """Display handicap marks for all events in tabular format.

    Shows one section per event with:
    - Competitor name
    - Predicted time
    - Handicap mark
    - Method used

    Args:
        tournament_state: Multi-event tournament state
    """
    print(f"\n{'?' + '?' * 68 + '?'}")
    title = f"HANDICAP MARKS - ALL EVENTS".center(68)
    print(f"{'?'}{title}{'?'}")
    print(f"{'?' + '?' * 68 + '?'}")

    if not tournament_state.get('events'):
        print("\n[WARN] No events in tournament.")
        input("\nPress Enter to continue...")
        return

    for event in tournament_state['events']:
        print(f"\n{'='*70}")
        print(f"  EVENT {event['event_order']}: {event['event_name']}")
        print(f"{'='*70}")
        print(f"Wood: {event['wood_diameter']}mm {event['wood_species']} (Quality {event['wood_quality']})")
        print(f"Event type: {event['event_code']}")
        print(f"{'='*70}")

        if not event['handicap_results_all']:
            print("\n[WARN] No handicaps calculated for this event.")
            continue

        # Display handicaps sorted by mark
        sorted_results = sorted(event['handicap_results_all'], key=lambda x: x['mark'])

        print(f"\n{'Competitor':<35s} {'Time':<10s} {'Mark':<6s} {'Method'}")
        print(f"{'-'*70}")

        for result in sorted_results:
            name = result['name'][:34]
            time = f"{result['predicted_time']:.1f}s"
            mark = f"{result['mark']}"
            method = result.get('method_used', 'Unknown')[:15]

            print(f"{name:<35s} {time:<10s} {mark:<6s} {method}")

        print(f"{'-'*70}")
        print(f"Total competitors: {len(event['handicap_results_all'])}")

    input("\nPress Enter to continue...")


def get_next_incomplete_round(tournament_state: Dict) -> Tuple[Optional[int], Optional[Dict], Optional[Dict]]:
    """Find next round that needs results entry.

    Searches events in order for the first pending or in-progress round.

    Args:
        tournament_state: Multi-event tournament state

    Returns:
        tuple: (event_index, event_obj, round_obj) or (None, None, None) if all complete
    """
    for event_idx, event in enumerate(tournament_state.get('events', [])):
        for round_obj in event.get('rounds', []):
            if round_obj['status'] in ['pending', 'in_progress']:
                return (event_idx, event, round_obj)

    return (None, None, None)


def display_event_progress(event_obj: Dict, current_round: Dict) -> None:
    """Display current event context and progress.

    Shows:
    - Event name and order
    - Round status (heats, semis, finals)
    - Current round being worked on
    - Next action required

    Args:
        event_obj: Event object
        current_round: Current round object being worked on
    """
    print(f"\n{'?' + '?' * 68 + '?'}")
    title = f"EVENT {event_obj['event_order']}: {event_obj['event_name']}".center(68)
    print(f"{'?'}{title}{'?'}")
    print(f"{'?' + '?' * 68 + '?'}")

    # Count rounds by type
    heats = [r for r in event_obj['rounds'] if r['round_type'] == 'heat']
    semis = [r for r in event_obj['rounds'] if r['round_type'] == 'semi']
    finals = [r for r in event_obj['rounds'] if r['round_type'] == 'final']

    # Display status
    def get_status_display(rounds):
        if not rounds:
            return "N/A"
        completed = sum(1 for r in rounds if r['status'] == 'completed')
        total = len(rounds)
        if completed == total:
            return f"[OK] Complete ({total}/{total})"
        elif completed > 0:
            return f"[WARN] In Progress ({completed}/{total})"
        else:
            return f"[ ] Pending (0/{total})"

    print(f"\nRound Status:")
    print(f"  Heats: {get_status_display(heats)}")
    if semis:
        print(f"  Semi-finals: {get_status_display(semis)}")
    if finals:
        print(f"  Finals: {get_status_display(finals)}")

    print(f"\nCurrent Round: {current_round['round_name']}")
    print(f"Competitors: {len(current_round['competitors'])}")
    print(f"Status: {current_round['status']}")


def sequential_results_workflow(tournament_state: Dict, wood_selection: Dict, heat_assignment_df: pd.DataFrame) -> Dict:
    """Sequential results entry workflow for all events in tournament.

    Guides judge through recording results for all rounds across all events.
    Navigation:
    - Auto-advance to next incomplete round
    - Show current event context
    - Allow jumping to specific event
    - Track overall progress

    Args:
        tournament_state: Multi-event tournament state
        wood_selection: Wood selection dict (legacy, not used in multi-event)
        heat_assignment_df: Heat assignment DataFrame (legacy, not used in multi-event)

    Returns:
        dict: Updated tournament_state with recorded results
    """
    print(f"\n{'?' + '?' * 68 + '?'}")
    title = f"SEQUENTIAL RESULTS ENTRY".center(68)
    print(f"{'?'}{title}{'?'}")
    print(f"{'?' + '?' * 68 + '?'}")

    # Validation: All events must have heats generated
    not_ready = [e for e in tournament_state.get('events', []) if e['status'] == 'pending' or e['status'] == 'configured']
    if not_ready:
        print(f"\n[WARN] ERROR: {len(not_ready)} event(s) not ready for results:")
        for event in not_ready:
            print(f"  - {event['event_name']}: {event['status']}")
        print("\nPlease generate schedule first (Option 5).")
        input("\nPress Enter to continue...")
        return tournament_state

    while True:
        # Find next incomplete round
        event_idx, event_obj, round_obj = get_next_incomplete_round(tournament_state)

        if event_idx is None:
            print(f"\n{'='*70}")
            print(f"  [OK] ALL EVENTS COMPLETED!")
            print(f"{'='*70}")
            print(f"All rounds across all events have been completed.")
            print(f"You can now generate the final tournament summary (Option 8).")
            input("\nPress Enter to continue...")
            break

        # Display current context
        display_event_progress(event_obj, round_obj)

        # Menu
        print(f"\n{'='*70}")
        print(f"  1) Record Results for {round_obj['round_name']}")
        print(f"  2) Jump to Specific Event")
        print(f"  3) View Tournament Status")
        print(f"  4) Return to Tournament Menu")
        print(f"{'='*70}")

        choice = input("\nYour choice: ").strip()

        if choice == '1':
            # Record results for current round
            print(f"\n{'='*70}")
            print(f"  RECORDING RESULTS: {round_obj['round_name']}")
            print(f"{'='*70}")

            # Prepare wood_selection for this event
            event_wood = {
                'species': event_obj['wood_species'],
                'size_mm': event_obj['wood_diameter'],
                'quality': event_obj['wood_quality'],
                'event': event_obj['event_code']
            }

            # Record results using existing function
            append_results_to_excel(
                heat_assignment_df,  # Legacy param (not used)
                event_wood,
                round_object=round_obj,
                tournament_state=None,  # Pass None to avoid single-event logic
                event_name=event_obj['event_name']  # Pass event name for HeatID
            )

            # Mark round in progress
            round_obj['status'] = 'in_progress'

            # Check if this is a final round
            is_final = round_obj['round_type'] == 'final'

            # Select advancers (if not final)
            if not is_final and event_obj['format'] != 'single_heat':
                advancers = select_heat_advancers(round_obj)
                print(f"\n[OK] {round_obj['round_name']} completed")
                print(f"[OK] Advancers: {', '.join(advancers)}")

                # Check if we need to generate next round
                current_round_type = round_obj['round_type']

                # Determine if more rounds needed
                all_heats = [r for r in event_obj['rounds'] if r['round_type'] == current_round_type]
                all_heats_complete = all(r['status'] == 'completed' for r in all_heats)

                if all_heats_complete:
                    # All heats/semis of this type complete - generate next round
                    all_advancers = []
                    for heat in all_heats:
                        all_advancers.extend(heat.get('advancers', []))

                    # Determine next round type
                    if current_round_type == 'heat':
                        if event_obj['format'] == 'heats_to_finals':
                            next_type = 'final'
                        else:  # heats_to_semis_to_finals
                            next_type = 'semi'
                    elif current_round_type == 'semi':
                        next_type = 'final'
                    else:
                        next_type = None

                    if next_type:
                        print(f"\n[OK] All {current_round_type}s complete")
                        print(f"[OK] Generating {next_type} round...")

                        target_count = None
                        if next_type == 'final':
                            target_count = event_obj.get('num_stands')
                        elif next_type == 'semi':
                            num_semis = event_obj.get('capacity_info', {}).get('num_semis', 2)
                            if event_obj.get('num_stands'):
                                target_count = event_obj['num_stands'] * num_semis

                        all_advancers = fill_advancers_with_random_draw(
                            all_heats,
                            all_advancers,
                            target_count,
                            round_label=next_type
                        )

                        # Generate next round using existing function
                        # Pass full event_obj - it has all required fields:
                        # rounds, all_competitors_df, wood_species, wood_diameter, wood_quality, event_code
                        next_rounds = generate_next_round(
                            event_obj,
                            all_advancers,
                            next_type,
                            is_championship=(event_obj.get('event_type') == 'championship')
                        )

                        # Add to event rounds
                        event_obj['rounds'].extend(next_rounds)
                        print(f"[OK] {len(next_rounds)} {next_type} round(s) generated")

            else:
                # Final round or single heat - mark event as complete
                round_obj['status'] = 'completed'
                print(f"\n[OK] {round_obj['round_name']} completed")

                if is_final:
                    event_obj['status'] = 'completed'
                    tournament_state['events_completed'] += 1
                    print(f"[OK] {event_obj['event_name']} COMPLETE!")

                    # Extract placements
                    event_obj['final_results'] = extract_event_placements(event_obj)

            # Update event status
            if event_obj['status'] != 'completed':
                event_obj['status'] = 'in_progress'

            # Auto-save
            auto_save_multi_event(tournament_state)

            input("\nPress Enter to continue to next round...")

        elif choice == '2':
            # Jump to specific event
            print(f"\n{'='*70}")
            print(f"  SELECT EVENT")
            print(f"{'='*70}")

            for i, event in enumerate(tournament_state['events'], 1):
                status = event['status']
                print(f"  {i}) {event['event_name']} ({status})")

            print(f"\n  0) Cancel")

            try:
                event_choice = int(input("\nSelect event (number): ").strip())
                if event_choice == 0:
                    continue

                if 1 <= event_choice <= len(tournament_state['events']):
                    tournament_state['current_event_index'] = event_choice - 1
                    print(f"\n[OK] Jumped to {tournament_state['events'][event_choice - 1]['event_name']}")
                else:
                    print("[WARN] Invalid selection")
            except ValueError:
                print("[WARN] Invalid input")

            input("\nPress Enter to continue...")

        elif choice == '3':
            # View tournament status
            view_tournament_schedule(tournament_state)

        elif choice == '4' or choice == '':
            break

        else:
            print("[WARN] Invalid selection")

    return tournament_state


def extract_event_placements(event_obj: Dict) -> Dict:
    """Extract top 3 placements from completed event.

    Finds final round and extracts finish order to determine
    1st, 2nd, and 3rd place finishers.

    Args:
        event_obj: Event object with completed finals

    Returns:
        dict: {
            'first_place': name,
            'second_place': name,
            'third_place': name,
            'all_placements': {name: position, ...}
        }
    """
    # Find final round
    final_rounds = [r for r in event_obj.get('rounds', []) if r['round_type'] == 'final']

    if not final_rounds:
        return {
            'first_place': None,
            'second_place': None,
            'third_place': None,
            'all_placements': {}
        }

    final_round = final_rounds[0]
    finish_order = final_round.get('finish_order', {})

    if not finish_order:
        return {
            'first_place': None,
            'second_place': None,
            'third_place': None,
            'all_placements': {}
        }

    # Sort by position (1st, 2nd, 3rd...)
    sorted_placements = sorted(finish_order.items(), key=lambda x: x[1])

    return {
        'first_place': sorted_placements[0][0] if len(sorted_placements) > 0 else None,
        'second_place': sorted_placements[1][0] if len(sorted_placements) > 1 else None,
        'third_place': sorted_placements[2][0] if len(sorted_placements) > 2 else None,
        'all_placements': finish_order
    }


def generate_tournament_summary(tournament_state: Dict) -> None:
    """Generate final tournament summary with top 3 in each event.

    Displays text-based summary showing:
    - Tournament name and date
    - For each event: event name and top 3 finishers with times
    - Tournament statistics

    Args:
        tournament_state: Multi-event tournament state
    """
    print(f"\n{'?' + '?' * 68 + '?'}")
    title = f"FINAL TOURNAMENT SUMMARY".center(68)
    print(f"{'?'}{title}{'?'}")
    print(f"{'?' + '?' * 68 + '?'}")

    print(f"\nTournament: {tournament_state.get('tournament_name', 'Unknown')}")
    print(f"Date: {tournament_state.get('tournament_date', 'Unknown')}")
    print(f"Total Events: {tournament_state.get('total_events', 0)}")

    # Validation: All events must be completed
    incomplete = [e for e in tournament_state.get('events', []) if e['status'] != 'completed']
    if incomplete:
        print(f"\n[WARN] WARNING: {len(incomplete)} event(s) not yet completed:")
        for event in incomplete:
            print(f"  - {event['event_name']}: {event['status']}")
        print("\nShowing results for completed events only.")

    # Display each event's results
    for event in tournament_state.get('events', []):
        print(f"\n{'='*70}")
        print(f"  EVENT {event['event_order']}: {event['event_name']}")
        print(f"{'='*70}")
        print(f"Wood: {event['wood_diameter']}mm {event['wood_species']} (Quality {event['wood_quality']})")
        print(f"Event type: {event['event_code']}")

        if event['status'] != 'completed':
            print(f"\n[WARN] Event not completed - no final results available")
            continue

        # Get placements
        results = event.get('final_results', {})

        if not results.get('first_place'):
            print(f"\n[WARN] No final results recorded")
            continue

        # Find final round to get times
        final_round = [r for r in event['rounds'] if r['round_type'] == 'final'][0]
        actual_results = final_round.get('actual_results', {})

        print(f"\n{'-'*70}")

        # Display top 3
        if results['first_place']:
            time = actual_results.get(results['first_place'], 'N/A')
            time_str = f"{time:.2f}s" if isinstance(time, (int, float)) else time
            print(f"  [1] 1st Place: {results['first_place']} ({time_str})")

        if results['second_place']:
            time = actual_results.get(results['second_place'], 'N/A')
            time_str = f"{time:.2f}s" if isinstance(time, (int, float)) else time
            print(f"  [2] 2nd Place: {results['second_place']} ({time_str})")

        if results['third_place']:
            time = actual_results.get(results['third_place'], 'N/A')
            time_str = f"{time:.2f}s" if isinstance(time, (int, float)) else time
            print(f"  [3] 3rd Place: {results['third_place']} ({time_str})")

        # Display payouts if configured (NEW V5.0)
        payout_config = event.get('payout_config')
        if payout_config and payout_config.get('enabled'):
            print(f"\n  PAYOUTS:")
            all_placements = results.get('all_placements', {})
            num_places = payout_config.get('num_places', 0)
            payouts = payout_config.get('payouts', {})

            # Display payouts for top 3 (or fewer if fewer paid places)
            for position in range(1, min(4, num_places + 1)):
                if position == 1 and results['first_place']:
                    name = results['first_place']
                elif position == 2 and results['second_place']:
                    name = results['second_place']
                elif position == 3 and results['third_place']:
                    name = results['third_place']
                else:
                    continue

                payout = payouts.get(position, 0)
                from woodchopping.ui.payout_ui import _get_ordinal
                print(f"    {_get_ordinal(position):6s}: ${payout:,.2f}")

            if num_places > 3:
                print(f"    ... plus {num_places - 3} more paid places")

            print(f"\n  Event Purse: ${payout_config['total_purse']:,.2f}")

    # Tournament statistics
    print(f"\n{'='*70}")
    print(f"  TOURNAMENT STATISTICS")
    print(f"{'='*70}")

    completed_events = [e for e in tournament_state['events'] if e['status'] == 'completed']
    total_competitors = sum(len(e['all_competitors']) for e in tournament_state['events'])
    total_rounds = sum(len(e['rounds']) for e in tournament_state['events'])

    print(f"Events completed: {len(completed_events)}/{tournament_state.get('total_events', 0)}")
    print(f"Total competitors: {total_competitors} (may include duplicates across events)")
    print(f"Total rounds run: {total_rounds}")

    # Tournament Earnings Summary (NEW V5.0)
    from woodchopping.ui.payout_ui import calculate_total_earnings, display_tournament_earnings_summary

    competitor_earnings = calculate_total_earnings(tournament_state)

    if competitor_earnings:
        print(f"\n{'='*70}")
        display_tournament_earnings_summary(tournament_state, competitor_earnings)

    print(f"\n{'='*70}")

    input("\nPress Enter to continue...")
