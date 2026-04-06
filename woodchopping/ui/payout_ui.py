"""
Payout Configuration and Display Module

This module provides functions for configuring and displaying prize money payouts
for woodchopping tournament events.

Functions:
    configure_event_payouts() - Interactive UI to configure payout structure
    display_payout_config() - Format payout config for inline display
    display_final_results_with_payouts() - Display final results with payouts
    calculate_total_earnings() - Aggregate earnings across all events
    display_tournament_earnings_summary() - Display earnings leaderboard
    display_single_event_final_results() - Helper for single-event final results
"""

from typing import Dict, Optional


def _get_ordinal(n: int) -> str:
    """Convert number to ordinal string (1st, 2nd, 3rd, etc.)

    Args:
        n: Position number

    Returns:
        str: Ordinal string (e.g., "1st", "2nd", "3rd")
    """
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def configure_event_payouts() -> Optional[Dict]:
    """Configure payout structure for an event.

    Prompts judge for:
    - Number of paid places (1-10)
    - Dollar amount per place
    - Displays total purse for confirmation

    Returns:
        dict: {
            'enabled': True,
            'num_places': int,
            'payouts': {1: 500.00, 2: 300.00, 3: 200.00, ...},
            'total_purse': float
        }
        or None if user cancels
    """
    print("╚" + "═" * 68 + "╝")
    print("║" + " " * 68 + "║")
    print("║" + "CONFIGURE EVENT PAYOUTS".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "═" * 68 + "╝")

    print("\nHow many places will be paid?")
    print("Enter 0 to skip payout configuration for this event.")

    while True:
        try:
            num_places_input = input("\nNumber of paid places (0-10): ").strip()
            if not num_places_input:
                return None

            num_places = int(num_places_input)

            if num_places == 0:
                return {"enabled": False}

            if num_places < 1 or num_places > 10:
                print("ERROR: Please enter a number between 0 and 10")
                continue

            break
        except ValueError:
            print("ERROR: Please enter a valid number")

    # Collect payout amounts
    payouts = {}
    for position in range(1, num_places + 1):
        while True:
            try:
                payout_str = input(f"\nPayout for {_get_ordinal(position)} place: $").strip()
                if not payout_str:
                    print("ERROR: Payout amount required")
                    continue

                payout = float(payout_str)

                if payout < 0:
                    print("ERROR: Payout must be positive")
                    continue

                payouts[position] = payout
                break
            except ValueError:
                print("ERROR: Please enter a valid dollar amount")

    # Calculate total purse
    total_purse = sum(payouts.values())

    # Display summary
    print("\n" + "╔" + "═" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "PAYOUT SUMMARY".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "═" * 68 + "╝")
    print()
    print("-" * 70)

    for position in range(1, num_places + 1):
        payout = payouts[position]
        print(f"{_get_ordinal(position):10s}     ${payout:,.2f}")

    print("-" * 70)
    print(f"{'Total Purse:':10s}     ${total_purse:,.2f}")
    print("-" * 70)

    # Confirm
    confirm = input("\nConfirm payout structure? (y/n): ").strip().lower()

    if confirm == "y":
        return {
            "enabled": True,
            "num_places": num_places,
            "payouts": payouts,
            "total_purse": total_purse,
        }
    else:
        print("\nPayout configuration cancelled")
        return None


def display_payout_config(payout_config: Dict) -> str:
    """Format payout config for inline display in menus.

    Args:
        payout_config: Payout configuration dict

    Returns:
        str: One-line summary (e.g., "Payouts: 3 places, $1,000.00 purse")
             or "Payouts: Not configured"
    """
    if not payout_config or not payout_config.get("enabled"):
        return "Payouts: Not configured"

    num_places = payout_config.get("num_places", 0)
    total_purse = payout_config.get("total_purse", 0.0)

    return f"Payouts: {num_places} places, ${total_purse:,.2f} purse"


def display_final_results_with_payouts(
    final_results: Dict, actual_times: Dict, payout_config: Dict, event_name: str
) -> None:
    """Display final event results with payouts.

    Shows:
    - Event banner
    - Top placements with times and payouts
    - Remaining placements (without payouts if outside top N)

    Args:
        final_results: {'first_place': name, 'second_place': name, ..., 'all_placements': {name: pos}}
        actual_times: {name: time} from final round
        payout_config: Payout configuration dict
        event_name: Event name for banner
    """
    print("\n" + "╔" + "═" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + f"FINAL RESULTS - {event_name}".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "═" * 68 + "╝")
    print()

    all_placements = final_results.get("all_placements", {})

    if not all_placements:
        print("No results available")
        return

    # Check if payouts are enabled
    payouts_enabled = payout_config and payout_config.get("enabled", False)

    # Print header
    if payouts_enabled:
        print(f"{'Place':<8s} {'Competitor':<30s} {'Time':<12s} {'Payout':<10s}")
        print("-" * 70)
    else:
        print(f"{'Place':<8s} {'Competitor':<30s} {'Time':<12s}")
        print("-" * 70)

    # Sort placements by position
    sorted_placements = sorted(all_placements.items(), key=lambda x: x[1])

    # Display each placement
    for name, position in sorted_placements:
        # Get time
        time = actual_times.get(name, "N/A")
        if isinstance(time, (int, float)):
            time_str = f"{time:.2f}s"
        else:
            time_str = str(time)

        # Get payout if applicable
        if payouts_enabled:
            num_places = payout_config.get("num_places", 0)
            if position <= num_places:
                payout = payout_config["payouts"].get(position, 0)
                payout_str = f"${payout:,.2f}"
            else:
                payout_str = "-"

            print(f"{_get_ordinal(position):<8s} {name:<30s} {time_str:<12s} {payout_str:<10s}")
        else:
            print(f"{_get_ordinal(position):<8s} {name:<30s} {time_str:<12s}")

    print("-" * 70)

    # Display total purse if payouts enabled
    if payouts_enabled:
        # Calculate actual paid amount (in case fewer finishers than paid places)
        actual_paid = sum(
            payout_config["payouts"].get(pos, 0)
            for pos in all_placements.values()
            if pos <= payout_config.get("num_places", 0)
        )

        print(f"\nTotal Purse Paid: ${actual_paid:,.2f}")

        # Check if fewer finishers than paid places
        if actual_paid < payout_config.get("total_purse", 0):
            unpaid = payout_config["total_purse"] - actual_paid
            print(f"Note: ${unpaid:,.2f} unpaid (fewer finishers than paid places)")


def calculate_total_earnings(tournament_state: Dict) -> Dict[str, float]:
    """Calculate total earnings per competitor across all completed events.

    Args:
        tournament_state: Multi-event tournament state

    Returns:
        dict: {competitor_name: total_earnings, ...}
              Sorted by earnings (descending)
    """
    competitor_earnings = {}

    # Iterate through all events
    for event in tournament_state.get("events", []):
        # Only process completed events
        if event.get("status") != "completed":
            continue

        # Check if payouts configured and enabled
        payout_config = event.get("payout_config")
        if not payout_config or not payout_config.get("enabled"):
            continue

        # Get final results
        final_results = event.get("final_results", {})
        all_placements = final_results.get("all_placements", {})

        if not all_placements:
            continue

        # Calculate payouts for this event
        num_places = payout_config.get("num_places", 0)
        payouts = payout_config.get("payouts", {})

        for competitor_name, position in all_placements.items():
            if position <= num_places:
                payout = payouts.get(position, 0)
                if payout > 0:
                    if competitor_name not in competitor_earnings:
                        competitor_earnings[competitor_name] = 0.0
                    competitor_earnings[competitor_name] += payout

    # Sort by earnings (descending)
    sorted_earnings = dict(sorted(competitor_earnings.items(), key=lambda x: x[1], reverse=True))

    return sorted_earnings


def display_tournament_earnings_summary(tournament_state: Dict, competitor_earnings: Dict[str, float]) -> None:
    """Display tournament-wide earnings summary.

    Shows:
    - Tournament banner
    - Earnings leaderboard (all competitors sorted by total)

    Args:
        tournament_state: Multi-event tournament state
        competitor_earnings: {competitor_name: total_earnings}
    """
    print("\n" + "╔" + "═" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "TOURNAMENT EARNINGS SUMMARY".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "═" * 68 + "╝")
    print()

    # Tournament info
    tournament_name = tournament_state.get("tournament_name", "Unknown Tournament")
    print(f"Tournament: {tournament_name}")

    # Count paid events and total purse
    paid_events_count = 0
    total_purse = 0.0

    for event in tournament_state.get("events", []):
        payout_config = event.get("payout_config")
        if payout_config and payout_config.get("enabled"):
            if event.get("status") == "completed":
                paid_events_count += 1
                # Calculate actual paid for this event
                final_results = event.get("final_results", {})
                all_placements = final_results.get("all_placements", {})
                num_places = payout_config.get("num_places", 0)
                payouts = payout_config.get("payouts", {})

                for position in all_placements.values():
                    if position <= num_places:
                        total_purse += payouts.get(position, 0)

    print(f"Paid Events: {paid_events_count}")
    print(f"Total Purse Paid: ${total_purse:,.2f}")
    print()

    # Earnings leaderboard
    print("EARNINGS LEADERBOARD")
    print("-" * 70)
    print(f"{'Rank':<8s} {'Competitor':<40s} {'Total Earnings':<15s}")
    print("-" * 70)

    if not competitor_earnings:
        print("No earnings to display")
    else:
        for rank, (competitor_name, earnings) in enumerate(competitor_earnings.items(), start=1):
            print(f"{rank:<8d} {competitor_name:<40s} ${earnings:,.2f}")

    print("-" * 70)


def display_single_event_final_results(tournament_state: Dict) -> None:
    """Display final results for completed single-event tournament.

    Shows:
    - Event name and configuration
    - Final placements with times
    - Payouts (if configured)

    Args:
        tournament_state: Single-event tournament state
    """
    # Validate tournament is complete
    if not tournament_state.get("rounds"):
        print("\n[WARN] No rounds exist yet")
        input("\nPress Enter to continue...")
        return

    # Find final round
    finals = [r for r in tournament_state["rounds"] if r.get("round_type") == "final"]

    if not finals:
        print("\n[WARN] Final round not yet run")
        input("\nPress Enter to continue...")
        return

    final_round = finals[0]

    if final_round.get("status") != "completed":
        print("\n[WARN] Final round not yet completed")
        input("\nPress Enter to continue...")
        return

    # Extract final round data
    finish_order = final_round.get("finish_order", {})
    actual_times = final_round.get("actual_results", {})

    if not finish_order:
        print("\n[WARN] No final results recorded")
        input("\nPress Enter to continue...")
        return

    # Create final_results dict (same structure as multi-event)
    sorted_placements = sorted(finish_order.items(), key=lambda x: x[1])

    final_results = {
        "first_place": sorted_placements[0][0] if len(sorted_placements) > 0 else None,
        "second_place": sorted_placements[1][0] if len(sorted_placements) > 1 else None,
        "third_place": sorted_placements[2][0] if len(sorted_placements) > 2 else None,
        "all_placements": finish_order,
    }

    # Display using payout display function
    display_final_results_with_payouts(
        final_results,
        actual_times,
        tournament_state.get("payout_config", {"enabled": False}),
        tournament_state.get("event_name", "Unknown Event"),
    )

    input("\nPress Enter to continue...")


def configure_tournament_payouts(tournament_state: Dict) -> Dict:
    """Configure payouts for events in a multi-event tournament.

    Allows judges to:
    - View current payout status for all events
    - Select an event to configure/modify payouts
    - Apply the same payout structure to multiple events

    Args:
        tournament_state: Multi-event tournament state dictionary

    Returns:
        dict: Updated tournament state
    """
    from woodchopping.ui.multi_event_ui import auto_save_multi_event

    while True:
        events = tournament_state.get("events", [])

        if not events:
            print("\n[WARN] No events configured in this tournament")
            input("\nPress Enter to continue...")
            return tournament_state

        # Display header
        print("\n╔" + "═" * 68 + "╗")
        print("║" + "CONFIGURE EVENT PAYOUTS".center(68) + "║")
        print("╚" + "═" * 68 + "╝")
        print("║" + f"Tournament: {tournament_state.get('tournament_name', 'Unknown')}".ljust(68) + "║")
        print("╚" + "═" * 68 + "╝")

        # Show all events with payout status
        print("\n  #   Event Name                    Payout Status")
        print("  " + "-" * 60)

        for i, event in enumerate(events, 1):
            event_name = event.get("event_name", f"Event {i}")[:25]
            payout_config = event.get("payout_config")

            if payout_config and payout_config.get("enabled"):
                num_places = payout_config.get("num_places", 0)
                total_purse = payout_config.get("total_purse", 0)
                status = f"${total_purse:,.0f} ({num_places} places)"
            else:
                status = "Not configured"

            print(f"  {i:<3} {event_name:<30} {status}")

        print("  " + "-" * 60)
        print("\n  C. Copy payout config from one event to others")
        print("  R. Return to Finance Menu")

        choice = input("\nSelect event number to configure, C to copy, or R to return: ").strip().lower()

        if choice == "r":
            return tournament_state

        if choice == "c":
            # Copy payout config from one event to others
            tournament_state = _copy_payout_config(tournament_state)
            continue

        # Try to select an event by number
        try:
            event_idx = int(choice) - 1
            if event_idx < 0 or event_idx >= len(events):
                print("\n[WARN] Invalid event number")
                input("\nPress Enter to continue...")
                continue

            # Configure payouts for selected event
            event = events[event_idx]
            event_name = event.get("event_name", f"Event {event_idx + 1}")

            print(f"\n{'=' * 60}")
            print(f"Configuring payouts for: {event_name}")
            print(f"{'=' * 60}")

            # Show current config if exists
            current_config = event.get("payout_config")
            if current_config and current_config.get("enabled"):
                print("\nCurrent configuration:")
                print(f"  Places paid: {current_config.get('num_places', 0)}")
                print(f"  Total purse: ${current_config.get('total_purse', 0):,.2f}")
                payouts = current_config.get("payouts", {})
                for pos in sorted(payouts.keys()):
                    print(f"    {_get_ordinal(pos)}: ${payouts[pos]:,.2f}")

                print("\nOptions:")
                print("  1. Modify payout configuration")
                print("  2. Remove payout configuration")
                print("  3. Cancel")

                modify_choice = input("\nChoice [1-3]: ").strip()

                if modify_choice == "2":
                    event["payout_config"] = {"enabled": False}
                    print(f"\n[OK] Payout configuration removed for {event_name}")
                    auto_save_multi_event(tournament_state)
                    input("\nPress Enter to continue...")
                    continue
                elif modify_choice != "1":
                    continue

            # Use existing configure_event_payouts function
            new_config = configure_event_payouts()

            if new_config:
                event["payout_config"] = new_config
                if new_config.get("enabled"):
                    print(f"\n[OK] Payout configuration saved for {event_name}")
                    print(f"  Total purse: ${new_config.get('total_purse', 0):,.2f}")
                else:
                    print(f"\n[OK] Payouts disabled for {event_name}")
                auto_save_multi_event(tournament_state)

            input("\nPress Enter to continue...")

        except ValueError:
            print("\n[WARN] Invalid choice")
            input("\nPress Enter to continue...")

    return tournament_state


def _copy_payout_config(tournament_state: Dict) -> Dict:
    """Copy payout configuration from one event to other events.

    Args:
        tournament_state: Multi-event tournament state dictionary

    Returns:
        dict: Updated tournament state
    """
    from woodchopping.ui.multi_event_ui import auto_save_multi_event

    events = tournament_state.get("events", [])

    # Find events with configured payouts
    configured_events = []
    for i, event in enumerate(events):
        payout_config = event.get("payout_config")
        if payout_config and payout_config.get("enabled"):
            configured_events.append((i, event))

    if not configured_events:
        print("\n[WARN] No events have payout configurations to copy from")
        print("Configure at least one event first.")
        input("\nPress Enter to continue...")
        return tournament_state

    print("\n╔" + "═" * 68 + "╗")
    print("║" + "COPY PAYOUT CONFIGURATION".center(68) + "║")
    print("╚" + "═" * 68 + "╝")

    # Show configured events to copy from
    print("\nSelect source event to copy FROM:")
    print("  " + "-" * 50)

    for idx, (i, event) in enumerate(configured_events, 1):
        event_name = event.get("event_name", f"Event {i + 1}")[:25]
        payout_config = event.get("payout_config")
        total_purse = payout_config.get("total_purse", 0)
        num_places = payout_config.get("num_places", 0)
        print(f"  {idx}. {event_name} - ${total_purse:,.0f} ({num_places} places)")

    print("  " + "-" * 50)

    try:
        source_choice = input("\nSelect source event number (or Enter to cancel): ").strip()
        if not source_choice:
            return tournament_state

        source_idx = int(source_choice) - 1
        if source_idx < 0 or source_idx >= len(configured_events):
            print("\n[WARN] Invalid selection")
            input("\nPress Enter to continue...")
            return tournament_state

        source_event_idx, source_event = configured_events[source_idx]
        source_config = source_event.get("payout_config").copy()

        # Show all other events to copy to
        print(f"\nSource: {source_event.get('event_name')} - ${source_config.get('total_purse', 0):,.0f}")
        print("\nSelect events to copy TO (comma-separated numbers, or 'all'):")
        print("  " + "-" * 50)

        target_events = []
        for i, event in enumerate(events):
            if i == source_event_idx:
                continue  # Skip source event
            event_name = event.get("event_name", f"Event {i + 1}")[:25]
            payout_config = event.get("payout_config")
            if payout_config and payout_config.get("enabled"):
                status = f"${payout_config.get('total_purse', 0):,.0f}"
            else:
                status = "Not configured"
            print(f"  {i + 1}. {event_name} ({status})")
            target_events.append(i)

        print("  " + "-" * 50)

        target_input = input("\nEnter event numbers or 'all': ").strip().lower()

        if target_input == "all":
            targets = target_events
        else:
            try:
                targets = [int(x.strip()) - 1 for x in target_input.split(",")]
                # Validate targets
                targets = [t for t in targets if t in target_events]
            except ValueError:
                print("\n[WARN] Invalid input")
                input("\nPress Enter to continue...")
                return tournament_state

        if not targets:
            print("\n[WARN] No valid target events selected")
            input("\nPress Enter to continue...")
            return tournament_state

        # Confirm
        print(f"\nThis will copy the payout configuration to {len(targets)} event(s).")
        confirm = input("Proceed? (y/n): ").strip().lower()

        if confirm == "y":
            for t in targets:
                events[t]["payout_config"] = source_config.copy()

            print(f"\n[OK] Payout configuration copied to {len(targets)} event(s)")
            auto_save_multi_event(tournament_state)

        input("\nPress Enter to continue...")

    except ValueError:
        print("\n[WARN] Invalid input")
        input("\nPress Enter to continue...")

    return tournament_state
