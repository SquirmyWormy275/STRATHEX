"""V5.2 UI Helper Functions for Tournament Entry Management.

These functions provide view, edit, and scratch management capabilities
for the new entry-form workflow.
"""

from typing import Dict

import pandas as pd


def view_tournament_entries(tournament_state: Dict) -> None:
    """Display tournament-wide entry summary (NEW V5.1).

    Shows:
    - Per competitor: Which events entered, fee status
    - Per event: Competitor count
    - Summary statistics

    Args:
        tournament_state: Multi-event tournament state
    """
    if not tournament_state.get("tournament_roster"):
        print("\n[WARN] No tournament roster configured")
        input("\nPress Enter to continue...")
        return

    roster = tournament_state["tournament_roster"]
    events = tournament_state["events"]
    fee_tracking = tournament_state.get("entry_fee_tracking_enabled", False)

    print(f"\n{'=' * 70}")
    print("  TOURNAMENT ENTRY SUMMARY")
    print(f"{'=' * 70}")
    print(f"Tournament: {tournament_state['tournament_name']}")
    print(f"Date: {tournament_state['tournament_date']}")
    print(f"Total Events: {len(events)}")
    print(f"Total Competitors: {len(roster)}")

    # Event summary
    print(f"\n{'=' * 70}")
    print("  EVENTS")
    print(f"{'=' * 70}")

    for event in events:
        comp_count = len(event.get("all_competitors", []))
        print(f"\n{event['event_name']}")
        print(f"  Type: {event['event_type'].upper()}")
        print(f"  Competitors: {comp_count}")
        print(f"  Status: {event['status'].upper()}")

    # Competitor summary
    print(f"\n{'=' * 70}")
    print("  COMPETITORS")
    print(f"{'=' * 70}")

    for comp in roster:
        comp_name = comp["competitor_name"]
        events_entered = comp["events_entered"]

        print(f"\n{comp_name}")

        if not events_entered:
            print("  [WARN] No events assigned")
            continue

        print(f"  Events ({len(events_entered)}):")

        for event_id in events_entered:
            event = next((e for e in events if e["event_id"] == event_id), None)
            if not event:
                continue

            event_name = event["event_name"]

            if fee_tracking:
                fee_paid = comp["entry_fees_paid"].get(event_id, False)
                status = "[OK] PAID" if fee_paid else "? UNPAID"
                print(f"    - {event_name} [{status}]")
            else:
                print(f"    - {event_name}")

    # Summary statistics
    print(f"\n{'=' * 70}")
    print("  SUMMARY STATISTICS")
    print(f"{'=' * 70}")

    total_entries = sum(len(comp["events_entered"]) for comp in roster)
    avg_events_per_comp = total_entries / len(roster) if roster else 0

    print(f"Total entries: {total_entries}")
    print(f"Average events per competitor: {avg_events_per_comp:.1f}")

    if fee_tracking:
        total_fees_paid = sum(sum(1 for paid in comp["entry_fees_paid"].values() if paid) for comp in roster)
        total_fees_unpaid = total_entries - total_fees_paid

        print(f"Entry fees paid: {total_fees_paid}/{total_entries}")
        print(f"Entry fees unpaid: {total_fees_unpaid}/{total_entries}")

    print(f"{'=' * 70}")

    input("\nPress Enter to continue...")


def edit_event_entries(tournament_state: Dict) -> Dict:
    """Edit event entries: add late entries, remove competitors, update fee status (NEW V5.1).

    Allows modifications after initial assignment but before heats generated.

    Args:
        tournament_state: Multi-event tournament state

    Returns:
        dict: Updated tournament_state
    """
    from woodchopping.ui.multi_event_ui import auto_save_multi_event

    if not tournament_state.get("tournament_roster"):
        print("\n[WARN] No tournament roster configured")
        input("\nPress Enter to continue...")
        return tournament_state

    roster = tournament_state["tournament_roster"]
    events = tournament_state["events"]
    fee_tracking = tournament_state.get("entry_fee_tracking_enabled", False)

    while True:
        print(f"\n{'=' * 70}")
        print("  EDIT EVENT ENTRIES")
        print(f"{'=' * 70}")
        print("\n1. Add competitor to event")
        print("2. Remove competitor from event")
        print("3. Update entry fee status")
        print("4. Return to main menu")

        choice = input("\nSelect option (1-4): ").strip()

        if choice == "4":
            break

        elif choice == "1":
            # Add competitor to event
            print(f"\n{'=' * 70}")
            print("  ADD COMPETITOR TO EVENT")
            print(f"{'=' * 70}")

            # Show competitors
            print("\nCompetitors:")
            for i, comp in enumerate(roster, 1):
                print(f"{i}. {comp['competitor_name']}")

            try:
                comp_idx = int(input("\nSelect competitor number: ").strip()) - 1
                comp = roster[comp_idx]
            except (ValueError, IndexError):
                print("[WARN] Invalid selection")
                continue

            # Show events
            print("\nEvents:")
            for i, event in enumerate(events, 1):
                assigned = "[OK]" if event["event_id"] in comp["events_entered"] else " "
                print(f"{i}. [{assigned}] {event['event_name']}")

            try:
                event_idx = int(input("\nSelect event number: ").strip()) - 1
                event = events[event_idx]
            except (ValueError, IndexError):
                print("[WARN] Invalid selection")
                continue

            # Check if already assigned
            if event["event_id"] in comp["events_entered"]:
                print(f"[WARN] {comp['competitor_name']} already entered in {event['event_name']}")
                continue

            # Check if heats already generated
            if event.get("rounds") and any(r.get("status") != "pending" for r in event["rounds"]):
                print(f"[WARN] Cannot add competitor - heats already generated for {event['event_name']}")
                print("   Use scratch management instead.")
                continue

            # Add assignment
            comp["events_entered"].append(event["event_id"])
            event["all_competitors"].append(comp["competitor_name"])

            # Update DataFrame
            comp_roster_df = tournament_state.get("competitor_roster_df")
            if comp_roster_df is not None and not comp_roster_df.empty:
                comp_row = comp_roster_df[comp_roster_df["competitor_name"] == comp["competitor_name"]]
                if not comp_row.empty:
                    event["all_competitors_df"] = pd.concat([event["all_competitors_df"], comp_row]).drop_duplicates()

            # Update competitor status
            event["competitor_status"][comp["competitor_name"]] = "active"

            # Entry fee
            if fee_tracking:
                fee_paid = input("Entry fee paid? (y/n): ").strip().lower()
                comp["entry_fees_paid"][event["event_id"]] = fee_paid == "y"

            print(f"\n[OK] {comp['competitor_name']} added to {event['event_name']}")

            # Auto-save
            auto_save_multi_event(tournament_state)

        elif choice == "2":
            # Remove competitor from event
            print(f"\n{'=' * 70}")
            print("  REMOVE COMPETITOR FROM EVENT")
            print(f"{'=' * 70}")

            # Show competitors
            print("\nCompetitors:")
            for i, comp in enumerate(roster, 1):
                print(f"{i}. {comp['competitor_name']} ({len(comp['events_entered'])} events)")

            try:
                comp_idx = int(input("\nSelect competitor number: ").strip()) - 1
                comp = roster[comp_idx]
            except (ValueError, IndexError):
                print("[WARN] Invalid selection")
                continue

            if not comp["events_entered"]:
                print(f"[WARN] {comp['competitor_name']} has no event entries")
                continue

            # Show their events
            print(f"\nEvents for {comp['competitor_name']}:")
            comp_events = [e for e in events if e["event_id"] in comp["events_entered"]]
            for i, event in enumerate(comp_events, 1):
                print(f"{i}. {event['event_name']}")

            try:
                event_idx = int(input("\nSelect event number to remove from: ").strip()) - 1
                event = comp_events[event_idx]
            except (ValueError, IndexError):
                print("[WARN] Invalid selection")
                continue

            # Check if heats already generated
            if event.get("rounds") and any(r.get("status") != "pending" for r in event["rounds"]):
                print(f"[WARN] Cannot remove competitor - heats already generated for {event['event_name']}")
                print("   Use scratch management instead.")
                continue

            # Confirm removal
            confirm = input(f"\nConfirm removal of {comp['competitor_name']} from {event['event_name']}? (y/n): ")
            if confirm.strip().lower() != "y":
                print("[WARN] Cancelled")
                continue

            # Remove assignment
            comp["events_entered"].remove(event["event_id"])
            event["all_competitors"].remove(comp["competitor_name"])

            # Update DataFrame
            event["all_competitors_df"] = event["all_competitors_df"][
                event["all_competitors_df"]["competitor_name"] != comp["competitor_name"]
            ]

            # Remove competitor status
            if comp["competitor_name"] in event["competitor_status"]:
                del event["competitor_status"][comp["competitor_name"]]

            # Remove entry fee tracking
            if event["event_id"] in comp["entry_fees_paid"]:
                del comp["entry_fees_paid"][event["event_id"]]

            print(f"\n[OK] {comp['competitor_name']} removed from {event['event_name']}")

            # Auto-save
            auto_save_multi_event(tournament_state)

        elif choice == "3":
            # Update entry fee status
            if not fee_tracking:
                print("\n[WARN] Entry fee tracking is disabled for this tournament")
                continue

            print(f"\n{'=' * 70}")
            print("  UPDATE ENTRY FEE STATUS")
            print(f"{'=' * 70}")

            # Show competitors with unpaid fees
            unpaid_comps = []
            for comp in roster:
                unpaid_events = [
                    event_id for event_id in comp["events_entered"] if not comp["entry_fees_paid"].get(event_id, False)
                ]
                if unpaid_events:
                    unpaid_comps.append((comp, unpaid_events))

            if not unpaid_comps:
                print("\n[OK] All entry fees paid!")
                continue

            print("\nCompetitors with unpaid fees:")
            for i, (comp, unpaid_events) in enumerate(unpaid_comps, 1):
                print(f"{i}. {comp['competitor_name']} - {len(unpaid_events)} unpaid")

            try:
                comp_idx = int(input("\nSelect competitor number: ").strip()) - 1
                comp, unpaid_events = unpaid_comps[comp_idx]
            except (ValueError, IndexError):
                print("[WARN] Invalid selection")
                continue

            # Show unpaid events
            print(f"\nUnpaid events for {comp['competitor_name']}:")
            unpaid_event_objs = [e for e in events if e["event_id"] in unpaid_events]
            for i, event in enumerate(unpaid_event_objs, 1):
                print(f"{i}. {event['event_name']}")

            try:
                event_idx = int(input("\nSelect event number to mark as paid: ").strip()) - 1
                event = unpaid_event_objs[event_idx]
            except (ValueError, IndexError):
                print("[WARN] Invalid selection")
                continue

            # Mark as paid
            comp["entry_fees_paid"][event["event_id"]] = True

            print(f"\n[OK] {comp['competitor_name']} - {event['event_name']} marked as PAID")

            # Auto-save
            auto_save_multi_event(tournament_state)

        else:
            print("[WARN] Invalid choice")

    return tournament_state


def manage_scratches(tournament_state: Dict) -> Dict:
    """Manage day-of competitor scratches (withdrawals) (NEW V5.1).

    For regular events: Remove from heats/rounds
    For bracket events: Auto-regenerate if before matches start, forfeit if during matches

    Args:
        tournament_state: Multi-event tournament state

    Returns:
        dict: Updated tournament_state
    """
    from woodchopping.ui.multi_event_ui import auto_save_multi_event

    if not tournament_state.get("tournament_roster"):
        print("\n[WARN] No tournament roster configured")
        input("\nPress Enter to continue...")
        return tournament_state

    roster = tournament_state["tournament_roster"]
    events = tournament_state["events"]

    print(f"\n{'=' * 70}")
    print("  SCRATCH MANAGEMENT")
    print(f"{'=' * 70}")
    print("\nManage day-of competitor withdrawals")

    # Show all active competitors across all events
    active_assignments = []
    for comp in roster:
        for event_id in comp["events_entered"]:
            event = next((e for e in events if e["event_id"] == event_id), None)
            if not event:
                continue

            comp_status = event["competitor_status"].get(comp["competitor_name"], "active")
            if comp_status == "active":
                active_assignments.append((comp, event))

    if not active_assignments:
        print("\n[WARN] No active competitor entries found")
        input("\nPress Enter to continue...")
        return tournament_state

    print("\nActive entries:")
    for i, (comp, event) in enumerate(active_assignments, 1):
        print(f"{i}. {comp['competitor_name']} - {event['event_name']}")

    print("\nSelect entry to scratch (or 'q' to quit):")

    selection = input("\nEntry number: ").strip()

    if selection.lower() == "q":
        return tournament_state

    try:
        idx = int(selection) - 1
        comp, event = active_assignments[idx]
    except (ValueError, IndexError):
        print("[WARN] Invalid selection")
        input("\nPress Enter to continue...")
        return tournament_state

    comp_name = comp["competitor_name"]
    event_name = event["event_name"]
    event_type = event["event_type"]

    # Confirm scratch
    print(f"\n{'=' * 70}")
    print("  CONFIRM SCRATCH")
    print(f"{'=' * 70}")
    print(f"Competitor: {comp_name}")
    print(f"Event: {event_name}")

    confirm = input("\nConfirm scratch? (y/n): ").strip().lower()
    if confirm != "y":
        print("[WARN] Scratch cancelled")
        input("\nPress Enter to continue...")
        return tournament_state

    # Mark as withdrawn in event
    event["competitor_status"][comp_name] = "withdrawn"

    # Handle based on event type
    if event_type == "bracket":
        # Bracket event - check if matches started
        rounds = event.get("rounds", [])

        if not rounds:
            # No bracket generated yet - simple removal
            print(f"\n[OK] {comp_name} removed from {event_name} (bracket not generated yet)")
            event["all_competitors"].remove(comp_name)
            event["all_competitors_df"] = event["all_competitors_df"][
                event["all_competitors_df"]["competitor_name"] != comp_name
            ]
            del event["competitor_status"][comp_name]

        else:
            # Bracket exists - check if any matches completed
            matches_completed = any(m.get("status") == "completed" for r in rounds for m in r.get("matches", []))

            if not matches_completed:
                # No matches completed - regenerate bracket
                print(f"\n{'=' * 70}")
                print("  REGENERATING BRACKET")
                print(f"{'=' * 70}")
                print(f"No matches completed yet. Regenerating bracket without {comp_name}...")

                # Remove from event
                event["all_competitors"].remove(comp_name)
                event["all_competitors_df"] = event["all_competitors_df"][
                    event["all_competitors_df"]["competitor_name"] != comp_name
                ]
                del event["competitor_status"][comp_name]

                # Regenerate bracket
                from woodchopping.ui.bracket_ui import (
                    generate_bracket_seeds,
                    generate_bracket_with_byes,
                )

                predictions = generate_bracket_seeds(
                    event["all_competitors_df"],
                    event["wood_species"],
                    event["wood_diameter"],
                    event["wood_quality"],
                    event["event_code"],
                )

                rounds = generate_bracket_with_byes(predictions)

                event["rounds"] = rounds
                event["predictions"] = predictions
                event["num_competitors"] = len(predictions)
                event["total_rounds"] = len(rounds)
                event["total_matches"] = sum(len(r["matches"]) for r in rounds)

                print(f"\n[OK] Bracket regenerated without {comp_name}")
                print(f"  New bracket: {len(predictions)} competitors, {len(rounds)} rounds")

            else:
                # Matches already started - mark as forfeit
                print(f"\n[WARN] Matches already in progress. {comp_name} marked as withdrawn.")
                print("   Their remaining matches will be forfeits.")

                # Mark all pending/in-progress matches as forfeits
                for round_obj in rounds:
                    for match in round_obj.get("matches", []):
                        if match.get("status") in ["pending", "in_progress"]:
                            if match.get("competitor1") == comp_name:
                                match["status"] = "forfeit"
                                match["winner"] = match.get("competitor2")
                                match["loser"] = comp_name
                                print(f"  - {match['match_id']}: {comp_name} forfeits")
                            elif match.get("competitor2") == comp_name:
                                match["status"] = "forfeit"
                                match["winner"] = match.get("competitor1")
                                match["loser"] = comp_name
                                print(f"  - {match['match_id']}: {comp_name} forfeits")

    else:
        # Regular event (handicap/championship) - remove from rounds
        rounds = event.get("rounds", [])

        if not rounds:
            # No heats generated yet - simple removal
            print(f"\n[OK] {comp_name} removed from {event_name} (heats not generated yet)")
            event["all_competitors"].remove(comp_name)
            event["all_competitors_df"] = event["all_competitors_df"][
                event["all_competitors_df"]["competitor_name"] != comp_name
            ]
            del event["competitor_status"][comp_name]

        else:
            # Heats exist - remove from all pending rounds
            for round_obj in rounds:
                if comp_name in round_obj.get("competitors", []):
                    if round_obj.get("status") == "pending":
                        # Remove from pending round
                        round_obj["competitors"].remove(comp_name)
                        round_obj["handicap_results"] = [
                            h for h in round_obj.get("handicap_results", []) if h.get("name") != comp_name
                        ]
                        print(f"  - Removed from {round_obj['round_name']}")
                    else:
                        # Round already started - mark as DNS (Did Not Start)
                        print(f"  - {round_obj['round_name']}: {comp_name} marked as DNS")

            print(f"\n[OK] {comp_name} scratched from {event_name}")

    # Auto-save
    auto_save_multi_event(tournament_state)

    input("\nPress Enter to continue...")

    return tournament_state
