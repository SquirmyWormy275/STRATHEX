"""Entry fee tracking and management UI.

This module provides tools for judges to track entry fee payments
for multi-event tournaments.
"""

from typing import Dict


def view_entry_fee_status(tournament_state: Dict) -> None:
    """Display entry fee payment status for all competitors and events.

    Shows:
    - Overall payment completion
    - Unpaid fees by competitor
    - Unpaid fees by event
    - Quick action to mark fees as paid

    Args:
        tournament_state: Multi-event tournament state
    """
    if not tournament_state.get("entry_fee_tracking_enabled"):
        print("\n[WARN] Entry fee tracking is not enabled for this tournament")
        print("Enable it when setting up the tournament roster (Option 3)")
        input("\nPress Enter to continue...")
        return

    roster = tournament_state.get("tournament_roster", [])
    events = tournament_state.get("events", [])

    if not roster:
        print("\n[WARN] No competitors in tournament roster")
        input("\nPress Enter to continue...")
        return

    # Calculate statistics
    total_entries = 0
    paid_entries = 0
    unpaid_by_competitor = {}
    unpaid_by_event = {}

    for comp in roster:
        comp_name = comp["competitor_name"]
        unpaid_events = []

        for event_id in comp.get("events_entered", []):
            total_entries += 1
            is_paid = comp.get("entry_fees_paid", {}).get(event_id, False)

            if is_paid:
                paid_entries += 1
            else:
                # Find event name
                event = next((e for e in events if e["event_id"] == event_id), None)
                event_name = event["event_name"] if event else event_id
                unpaid_events.append(event_name)

                # Track by event
                if event_name not in unpaid_by_event:
                    unpaid_by_event[event_name] = []
                unpaid_by_event[event_name].append(comp_name)

        if unpaid_events:
            unpaid_by_competitor[comp_name] = unpaid_events

    # Display report
    print("\n╔" + "═" * 68 + "╗")
    print("║" + "ENTRY FEE PAYMENT STATUS".center(68) + "║")
    print("╚" + "═" * 68 + "╝")

    # Overall status
    percent_paid = int((paid_entries / total_entries * 100)) if total_entries > 0 else 0
    print("║" + f"  Total Entries: {total_entries}".ljust(68) + "║")
    print("║" + f"  Paid: {paid_entries} ({percent_paid}%)".ljust(68) + "║")
    print("║" + f"  Unpaid: {total_entries - paid_entries}".ljust(68) + "║")

    if unpaid_by_competitor:
        print("╚" + "═" * 68 + "╝")
        print("║" + "  UNPAID FEES BY COMPETITOR".ljust(68) + "║")
        print("╚" + "═" * 68 + "╝")

        for comp_name, event_list in sorted(unpaid_by_competitor.items()):
            # Truncate name if too long
            display_name = comp_name[:30] if len(comp_name) > 30 else comp_name
            print("║" + f"  {display_name}".ljust(68) + "║")

            for event_name in event_list:
                # Truncate event name if needed
                display_event = event_name[:50] if len(event_name) > 50 else event_name
                print("║" + f"    - {display_event}".ljust(68) + "║")

    if unpaid_by_event:
        print("╚" + "═" * 68 + "╝")
        print("║" + "  UNPAID FEES BY EVENT".ljust(68) + "║")
        print("╚" + "═" * 68 + "╝")

        for event_name, comp_list in sorted(unpaid_by_event.items()):
            display_event = event_name[:50] if len(event_name) > 50 else event_name
            print("║" + f"  {display_event} ({len(comp_list)} unpaid)".ljust(68) + "║")

    print("╚" + "═" * 68 + "╝")

    # Quick action menu
    if unpaid_by_competitor:
        print("\nOPTIONS:")
        print("  1. Mark fees as paid (by competitor)")
        print("  2. Mark fees as paid (by event)")
        print("  3. View detailed payment grid")
        print("  4. Return to menu")

        choice = input("\nChoice [1-4]: ").strip()

        if choice == "1":
            mark_fees_paid_by_competitor(tournament_state, unpaid_by_competitor)
        elif choice == "2":
            mark_fees_paid_by_event(tournament_state, unpaid_by_event)
        elif choice == "3":
            display_payment_grid(tournament_state)
        else:
            return
    else:
        print("\n[OK] All entry fees paid!")
        input("\nPress Enter to continue...")


def mark_fees_paid_by_competitor(tournament_state: Dict, unpaid_by_competitor: Dict) -> None:
    """Mark entry fees as paid for a specific competitor.

    Args:
        tournament_state: Multi-event tournament state
        unpaid_by_competitor: Dict mapping competitor names to unpaid events
    """
    print("\n╔" + "═" * 68 + "╗")
    print("║" + "MARK FEES PAID - BY COMPETITOR".center(68) + "║")
    print("╚" + "═" * 68 + "╝")

    comp_list = sorted(unpaid_by_competitor.keys())
    for idx, comp_name in enumerate(comp_list, 1):
        print("║" + f"  {idx}. {comp_name}".ljust(68) + "║")

    print("╚" + "═" * 68 + "╝")

    try:
        choice = int(input("\nSelect competitor (number): ").strip())
        if 1 <= choice <= len(comp_list):
            selected_comp = comp_list[choice - 1]

            # Find competitor in roster
            roster = tournament_state["tournament_roster"]
            comp_obj = next((c for c in roster if c["competitor_name"] == selected_comp), None)

            if not comp_obj:
                print("\n[WARN] Competitor not found")
                input("\nPress Enter to continue...")
                return

            # Show unpaid events for this competitor
            unpaid_events = unpaid_by_competitor[selected_comp]
            print(f"\nUnpaid events for {selected_comp}:")
            for idx, event_name in enumerate(unpaid_events, 1):
                print(f"  {idx}. {event_name}")

            # Find event IDs
            events = tournament_state.get("events", [])
            event_ids = []
            for event_name in unpaid_events:
                event = next((e for e in events if e["event_name"] == event_name), None)
                if event:
                    event_ids.append(event["event_id"])

            # Confirm
            confirm = input(f"\nMark all {len(unpaid_events)} fees as PAID? (y/n): ").strip().lower()
            if confirm == "y":
                for event_id in event_ids:
                    comp_obj["entry_fees_paid"][event_id] = True

                # Auto-save
                from woodchopping.ui.multi_event_ui import auto_save_multi_event

                auto_save_multi_event(tournament_state)

                print(f"\n[OK] {len(event_ids)} fee(s) marked as paid for {selected_comp}")
                input("\nPress Enter to continue...")
            else:
                print("\nCancelled")
                input("\nPress Enter to continue...")
        else:
            print("\n[WARN] Invalid selection")
            input("\nPress Enter to continue...")
    except ValueError:
        print("\n[WARN] Invalid input")
        input("\nPress Enter to continue...")


def mark_fees_paid_by_event(tournament_state: Dict, unpaid_by_event: Dict) -> None:
    """Mark entry fees as paid for all competitors in a specific event.

    Args:
        tournament_state: Multi-event tournament state
        unpaid_by_event: Dict mapping event names to unpaid competitors
    """
    print("\n╔" + "═" * 68 + "╗")
    print("║" + "MARK FEES PAID - BY EVENT".center(68) + "║")
    print("╚" + "═" * 68 + "╝")

    event_list = sorted(unpaid_by_event.keys())
    for idx, event_name in enumerate(event_list, 1):
        comp_count = len(unpaid_by_event[event_name])
        print("║" + f"  {idx}. {event_name} ({comp_count} unpaid)".ljust(68) + "║")

    print("╚" + "═" * 68 + "╝")

    try:
        choice = int(input("\nSelect event (number): ").strip())
        if 1 <= choice <= len(event_list):
            selected_event = event_list[choice - 1]
            unpaid_comps = unpaid_by_event[selected_event]

            # Find event ID
            events = tournament_state.get("events", [])
            event = next((e for e in events if e["event_name"] == selected_event), None)

            if not event:
                print("\n[WARN] Event not found")
                input("\nPress Enter to continue...")
                return

            event_id = event["event_id"]

            # Show unpaid competitors
            print(f"\nUnpaid fees for {selected_event}:")
            for comp_name in unpaid_comps:
                print(f"  - {comp_name}")

            # Confirm
            confirm = input(f"\nMark all {len(unpaid_comps)} fees as PAID? (y/n): ").strip().lower()
            if confirm == "y":
                roster = tournament_state["tournament_roster"]
                marked_count = 0

                for comp_name in unpaid_comps:
                    comp_obj = next((c for c in roster if c["competitor_name"] == comp_name), None)
                    if comp_obj:
                        comp_obj["entry_fees_paid"][event_id] = True
                        marked_count += 1

                # Auto-save
                from woodchopping.ui.multi_event_ui import auto_save_multi_event

                auto_save_multi_event(tournament_state)

                print(f"\n[OK] {marked_count} fee(s) marked as paid for {selected_event}")
                input("\nPress Enter to continue...")
            else:
                print("\nCancelled")
                input("\nPress Enter to continue...")
        else:
            print("\n[WARN] Invalid selection")
            input("\nPress Enter to continue...")
    except ValueError:
        print("\n[WARN] Invalid input")
        input("\nPress Enter to continue...")


def display_payment_grid(tournament_state: Dict) -> None:
    """Display a grid showing payment status for all competitors and events.

    Args:
        tournament_state: Multi-event tournament state
    """
    roster = tournament_state.get("tournament_roster", [])
    events = tournament_state.get("events", [])

    if not roster or not events:
        print("\n[WARN] No data to display")
        input("\nPress Enter to continue...")
        return

    print("\n╔" + "═" * 68 + "╗")
    print("║" + "PAYMENT GRID".center(68) + "║")
    print("╚" + "═" * 68 + "╝")
    print("║" + "Legend: [OK] = Paid, ? = Unpaid, - = Not entered".ljust(68) + "║")
    print("╚" + "═" * 68 + "╝")

    # Build grid
    print("\n" + "=" * 70)

    # Header with event names (abbreviated)
    event_abbrevs = []
    for event in events:
        # Abbreviate event name to 10 chars max
        abbrev = event["event_name"][:10]
        event_abbrevs.append(abbrev)

    header = "Competitor".ljust(30) + " | " + " | ".join(f"{abbrev:10s}" for abbrev in event_abbrevs)
    print(header)
    print("-" * len(header))

    # Data rows
    for comp in roster:
        comp_name = comp["competitor_name"][:28]  # Truncate if needed
        row = f"{comp_name:30s}"

        for event in events:
            event_id = event["event_id"]

            if event_id in comp.get("events_entered", []):
                is_paid = comp.get("entry_fees_paid", {}).get(event_id, False)
                symbol = "[OK]" if is_paid else "?"
            else:
                symbol = "-"

            row += f" | {symbol:^10s}"

        print(row)

    print("=" * 70)
    input("\nPress Enter to continue...")
