"""Scratch/withdrawal management for tournaments.

This module handles day-of scratches and withdrawals:
- Mark competitors as scratched
- Remove from pending events
- Recalculate heats/brackets
- Track scratch history
"""

from datetime import datetime
from typing import Dict


def manage_tournament_scratches(tournament_state: Dict) -> Dict:
    """Main scratch management interface for multi-event tournaments.

    Allows judges to:
    - View all competitors
    - Mark as scratched (with reason)
    - Remove from pending events
    - Recalculate affected heats/brackets

    Args:
        tournament_state: Multi-event tournament state

    Returns:
        dict: Updated tournament_state
    """
    while True:
        print("\n╔" + "═" * 68 + "╗")
        print("║" + "SCRATCH/WITHDRAWAL MANAGEMENT".center(68) + "║")
        print("╠" + "═" * 68 + "╣")

        # Count scratches
        roster = tournament_state.get("tournament_roster", [])
        scratch_count = sum(1 for c in roster if c.get("status") == "scratched")

        print("║" + f"  Tournament: {tournament_state.get('tournament_name', 'Unknown')}".ljust(68) + "║")
        print("║" + f"  Total competitors: {len(roster)}".ljust(68) + "║")
        print("║" + f"  Scratched: {scratch_count}".ljust(68) + "║")
        print("╠" + "═" * 68 + "╣")
        print("║" + "  1. View All Competitors".ljust(68) + "║")
        print("║" + "  2. Mark Competitor as Scratched".ljust(68) + "║")
        print("║" + "  3. View Scratch History".ljust(68) + "║")
        print("║" + "  4. Restore Scratched Competitor (Undo)".ljust(68) + "║")
        print("║" + "  5. Return to Main Menu".ljust(68) + "║")
        print("╠" + "═" * 68 + "╣")

        choice = input("\nChoice [1-5]: ").strip()

        if choice == "1":
            view_all_competitors_with_status(tournament_state)
        elif choice == "2":
            tournament_state = mark_competitor_scratched(tournament_state)
        elif choice == "3":
            view_scratch_history(tournament_state)
        elif choice == "4":
            tournament_state = restore_scratched_competitor(tournament_state)
        elif choice == "5" or choice == "":
            break
        else:
            print("\n[WARN] Invalid choice")
            input("\nPress Enter to continue...")

    return tournament_state


def view_all_competitors_with_status(tournament_state: Dict) -> None:
    """Display all competitors with their status and event assignments.

    Args:
        tournament_state: Multi-event tournament state
    """
    roster = tournament_state.get("tournament_roster", [])
    events = tournament_state.get("events", [])

    if not roster:
        print("\n[WARN] No competitors in tournament")
        input("\nPress Enter to continue...")
        return

    print("\n╔" + "═" * 68 + "╗")
    print("║" + "COMPETITOR STATUS".center(68) + "║")
    print("╠" + "═" * 68 + "╣")

    active_count = 0
    scratched_count = 0

    for idx, comp in enumerate(roster, 1):
        name = comp["competitor_name"]
        status = comp.get("status", "active")
        events_entered = comp.get("events_entered", [])

        # Count events
        event_names = []
        for event_id in events_entered:
            event = next((e for e in events if e["event_id"] == event_id), None)
            if event:
                event_names.append(event["event_name"][:20])  # Truncate

        if status == "scratched":
            status_icon = "✗ SCRATCHED"
            scratched_count += 1
        else:
            status_icon = "[OK] Active"
            active_count += 1

        # Truncate name if needed
        display_name = name[:30] if len(name) > 30 else name

        print("║" + f"  {idx:3d}. {display_name:30s} {status_icon}".ljust(68) + "║")

        if events_entered:
            events_str = f"       Events: {len(events_entered)}"
            print("║" + events_str.ljust(68) + "║")

    print("╠" + "═" * 68 + "╣")
    print("║" + f"  Active: {active_count}  |  Scratched: {scratched_count}".ljust(68) + "║")
    print("╠" + "═" * 68 + "╣")
    input("\nPress Enter to continue...")


def mark_competitor_scratched(tournament_state: Dict) -> Dict:
    """Mark a competitor as scratched and remove from pending events.

    Workflow:
    1. Select competitor
    2. Enter scratch reason
    3. Confirm action
    4. Mark as scratched
    5. Remove from pending events
    6. Offer to recalculate heats/brackets

    Args:
        tournament_state: Multi-event tournament state

    Returns:
        dict: Updated tournament_state
    """
    roster = tournament_state.get("tournament_roster", [])
    active_roster = [c for c in roster if c.get("status", "active") == "active"]

    if not active_roster:
        print("\n[WARN] No active competitors to scratch")
        input("\nPress Enter to continue...")
        return tournament_state

    print("\n╔" + "═" * 68 + "╗")
    print("║" + "MARK COMPETITOR AS SCRATCHED".center(68) + "║")
    print("╠" + "═" * 68 + "╣")

    for idx, comp in enumerate(active_roster, 1):
        name = comp["competitor_name"]
        events_count = len(comp.get("events_entered", []))
        print("║" + f"  {idx:3d}. {name:40s} ({events_count} events)".ljust(68) + "║")

    print("╠" + "═" * 68 + "╣")

    try:
        choice = int(input("\nSelect competitor to scratch (number, or 0 to cancel): ").strip())

        if choice == 0:
            print("\nCancelled")
            input("\nPress Enter to continue...")
            return tournament_state

        if 1 <= choice <= len(active_roster):
            selected_comp = active_roster[choice - 1]
            comp_name = selected_comp["competitor_name"]
            events_entered = selected_comp.get("events_entered", [])

            # Show events they're in
            print(f"\n{comp_name} is entered in {len(events_entered)} event(s)")

            # Get scratch reason
            print("\nCommon reasons:")
            print("  1. Injury")
            print("  2. Personal emergency")
            print("  3. No-show")
            print("  4. Equipment failure")
            print("  5. Other")

            reason_choice = input("\nSelect reason (1-5) or enter custom: ").strip()

            reasons = {
                "1": "Injury",
                "2": "Personal emergency",
                "3": "No-show",
                "4": "Equipment failure",
                "5": "Other",
            }

            if reason_choice in reasons:
                reason = reasons[reason_choice]
                if reason == "Other":
                    reason = input("Enter custom reason: ").strip()
            else:
                reason = reason_choice if reason_choice else "No reason given"

            # Confirm
            print(f"\n{'=' * 70}")
            print("  CONFIRM SCRATCH")
            print(f"{'=' * 70}")
            print(f"  Competitor: {comp_name}")
            print(f"  Reason: {reason}")
            print(f"  Will be removed from {len(events_entered)} event(s)")
            print(f"{'=' * 70}")

            confirm = input("\nConfirm scratch? (yes/no): ").strip().lower()

            if confirm in ["yes", "y"]:
                # Mark as scratched
                selected_comp["status"] = "scratched"
                selected_comp["scratch_reason"] = reason
                selected_comp["scratch_timestamp"] = datetime.now().isoformat(timespec="seconds")

                # Initialize scratch history if not exists
                if "scratch_history" not in tournament_state:
                    tournament_state["scratch_history"] = []

                # Add to history
                tournament_state["scratch_history"].append(
                    {
                        "competitor_name": comp_name,
                        "reason": reason,
                        "timestamp": selected_comp["scratch_timestamp"],
                        "events_affected": events_entered.copy(),
                    }
                )

                # Remove from events
                events = tournament_state.get("events", [])
                affected_events = []

                for event in events:
                    event_id = event["event_id"]

                    if event_id in events_entered:
                        # Remove from all_competitors list
                        if comp_name in event.get("all_competitors", []):
                            event["all_competitors"].remove(comp_name)
                            affected_events.append(event["event_name"])

                        # Update competitor_status
                        if "competitor_status" in event:
                            event["competitor_status"][comp_name] = "scratched"

                        # Remove from rounds if not yet completed
                        for round_obj in event.get("rounds", []):
                            if round_obj.get("status") == "pending":
                                if comp_name in round_obj.get("competitors", []):
                                    round_obj["competitors"].remove(comp_name)

                                # Remove from handicap_results
                                if "handicap_results" in round_obj:
                                    round_obj["handicap_results"] = [
                                        r for r in round_obj["handicap_results"] if r.get("name") != comp_name
                                    ]

                # Auto-save
                from woodchopping.ui.multi_event_ui import auto_save_multi_event

                auto_save_multi_event(tournament_state)

                print(f"\n[OK] {comp_name} marked as SCRATCHED")
                print(f"[OK] Removed from {len(affected_events)} event(s):")
                for event_name in affected_events:
                    print(f"  - {event_name}")

                # Offer to recalculate heats
                if affected_events:
                    recalc = input("\nRecalculate heats for affected events? (y/n): ").strip().lower()
                    if recalc == "y":
                        print("\n[WARN] Heat recalculation not yet implemented")
                        print("Please regenerate heats manually if needed")

                input("\nPress Enter to continue...")
            else:
                print("\nScratch cancelled")
                input("\nPress Enter to continue...")
        else:
            print("\n[WARN] Invalid selection")
            input("\nPress Enter to continue...")
    except ValueError:
        print("\n[WARN] Invalid input")
        input("\nPress Enter to continue...")

    return tournament_state


def view_scratch_history(tournament_state: Dict) -> None:
    """Display history of all scratches for this tournament.

    Args:
        tournament_state: Multi-event tournament state
    """
    history = tournament_state.get("scratch_history", [])

    if not history:
        print("\n[OK] No scratches recorded for this tournament")
        input("\nPress Enter to continue...")
        return

    print("\n╔" + "═" * 68 + "╗")
    print("║" + "SCRATCH HISTORY".center(68) + "║")
    print("╠" + "═" * 68 + "╣")

    for idx, record in enumerate(history, 1):
        comp_name = record["competitor_name"]
        reason = record["reason"]
        timestamp = record["timestamp"]
        events_affected = record.get("events_affected", [])

        print("║" + f"  {idx}. {comp_name}".ljust(68) + "║")
        print("║" + f"     Reason: {reason}".ljust(68) + "║")
        print("║" + f"     Time: {timestamp}".ljust(68) + "║")
        print("║" + f"     Events affected: {len(events_affected)}".ljust(68) + "║")
        print("║" + " " * 68 + "║")

    print("╠" + "═" * 68 + "╣")
    input("\nPress Enter to continue...")


def restore_scratched_competitor(tournament_state: Dict) -> Dict:
    """Restore a scratched competitor back to active status.

    Use case: Competitor shows up after being marked scratched,
    or judge accidentally scratched wrong person.

    Args:
        tournament_state: Multi-event tournament state

    Returns:
        dict: Updated tournament_state
    """
    roster = tournament_state.get("tournament_roster", [])
    scratched_roster = [c for c in roster if c.get("status") == "scratched"]

    if not scratched_roster:
        print("\n[OK] No scratched competitors to restore")
        input("\nPress Enter to continue...")
        return tournament_state

    print("\n╔" + "═" * 68 + "╗")
    print("║" + "RESTORE SCRATCHED COMPETITOR".center(68) + "║")
    print("╠" + "═" * 68 + "╣")

    for idx, comp in enumerate(scratched_roster, 1):
        name = comp["competitor_name"]
        reason = comp.get("scratch_reason", "Unknown")
        print("║" + f"  {idx}. {name:40s}".ljust(68) + "║")
        print("║" + f"     Reason: {reason}".ljust(68) + "║")

    print("╠" + "═" * 68 + "╣")

    try:
        choice = int(input("\nSelect competitor to restore (number, or 0 to cancel): ").strip())

        if choice == 0:
            print("\nCancelled")
            input("\nPress Enter to continue...")
            return tournament_state

        if 1 <= choice <= len(scratched_roster):
            selected_comp = scratched_roster[choice - 1]
            comp_name = selected_comp["competitor_name"]

            confirm = input(f"\nRestore {comp_name} to active status? (y/n): ").strip().lower()

            if confirm == "y":
                # Restore status
                selected_comp["status"] = "active"

                # Re-add to events
                events = tournament_state.get("events", [])
                events_entered = selected_comp.get("events_entered", [])
                restored_events = []

                for event in events:
                    event_id = event["event_id"]

                    if event_id in events_entered:
                        # Add back to all_competitors
                        if comp_name not in event.get("all_competitors", []):
                            event["all_competitors"].append(comp_name)
                            restored_events.append(event["event_name"])

                        # Update competitor_status
                        if "competitor_status" in event:
                            event["competitor_status"][comp_name] = "active"

                # Auto-save
                from woodchopping.ui.multi_event_ui import auto_save_multi_event

                auto_save_multi_event(tournament_state)

                print(f"\n[OK] {comp_name} restored to ACTIVE status")
                print(f"[OK] Restored to {len(restored_events)} event(s)")

                print("\n[WARN] NOTE: Competitor will need to be manually added back to heats")
                print("   Use 'Regenerate Schedule' if heats have not started")

                input("\nPress Enter to continue...")
            else:
                print("\nRestore cancelled")
                input("\nPress Enter to continue...")
        else:
            print("\n[WARN] Invalid selection")
            input("\nPress Enter to continue...")
    except ValueError:
        print("\n[WARN] Invalid input")
        input("\nPress Enter to continue...")

    return tournament_state


def check_competitor_status(tournament_state: Dict, competitor_name: str) -> str:
    """Check if a competitor is active or scratched.

    Args:
        tournament_state: Multi-event tournament state
        competitor_name: Name of competitor to check

    Returns:
        str: 'active' or 'scratched'
    """
    roster = tournament_state.get("tournament_roster", [])
    comp = next((c for c in roster if c["competitor_name"] == competitor_name), None)

    if comp:
        return comp.get("status", "active")
    return "active"  # Default if not found


def get_scratch_count(tournament_state: Dict) -> int:
    """Get total number of scratched competitors.

    Args:
        tournament_state: Multi-event tournament state

    Returns:
        int: Number of scratched competitors
    """
    roster = tournament_state.get("tournament_roster", [])
    return sum(1 for c in roster if c.get("status") == "scratched")
