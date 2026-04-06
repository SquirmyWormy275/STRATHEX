# -*- coding: utf-8 -*-
"""
Schedule Printout Generator (A1)

Generates formatted, printable tournament schedules for:
- Single-event tournaments
- Multi-event tournaments (combined schedule for entire day)

Exports to TXT file with 70-character width standard.
"""

import os
from datetime import datetime
from typing import Dict, List


def generate_printable_schedule(tournament_state: Dict) -> str:
    """
    Generate a formatted, printable tournament schedule.

    Supports both single-event and multi-event tournaments.
    For multi-event: generates combined schedule for entire tournament day.

    Args:
        tournament_state: Tournament state dict (single or multi-event)

    Returns:
        Formatted schedule string + saves to TXT file
    """
    # Detect tournament type
    is_multi_event = tournament_state.get("tournament_mode") == "multi_event"

    if is_multi_event:
        schedule_text = _generate_multi_event_schedule(tournament_state)
        filename = _generate_filename(tournament_state.get("tournament_name", "Tournament"))
    else:
        schedule_text = _generate_single_event_schedule(tournament_state)
        filename = _generate_filename(tournament_state.get("event_name", "Event"))

    # Save to file
    filepath = os.path.join(os.getcwd(), filename)
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(schedule_text)
        print(f"\n[OK] Schedule exported to: {filepath}")
    except Exception as e:
        print(f"\n[WARN] Error saving schedule file: {e}")

    return schedule_text


def _generate_filename(base_name: str) -> str:
    """Generate filename with timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Clean base name (remove special characters)
    clean_name = "".join(c if c.isalnum() or c in (" ", "_") else "_" for c in base_name)
    clean_name = clean_name.replace(" ", "_")
    return f"{clean_name}_schedule_{timestamp}.txt"


def _generate_single_event_schedule(tournament_state: Dict) -> str:
    """Generate schedule for single-event tournament."""
    lines = []

    # Header
    lines.append("╔" + "═" * 68 + "╗")
    lines.append("║" + "TOURNAMENT SCHEDULE".center(68) + "║")
    lines.append("╠" + "═" * 68 + "╣")

    # Event details
    event_name = tournament_state.get("event_name", "Unknown Event")
    lines.append("║" + f"  Event: {event_name}".ljust(68) + "║")

    # Wood details
    wood_species = tournament_state.get("wood_species", "Unknown")
    wood_diameter = tournament_state.get("wood_diameter", 0)
    wood_quality = tournament_state.get("wood_quality", 0)
    wood_line = f"  Wood: {wood_species}, {wood_diameter}mm, Quality {wood_quality}"
    lines.append("║" + wood_line.ljust(68) + "║")

    # Tournament format
    format_type = tournament_state.get("format", "Unknown")
    num_stands = tournament_state.get("num_stands", 0)
    format_line = f"  Format: {format_type} | {num_stands} stands available"
    lines.append("║" + format_line.ljust(68) + "║")

    lines.append("╠" + "═" * 68 + "╣")

    # Rounds
    rounds = tournament_state.get("rounds", [])
    if not rounds:
        lines.append("║" + "  No rounds generated yet".center(68) + "║")
    else:
        for round_obj in rounds:
            _add_round_to_schedule(lines, round_obj)

    lines.append("╚" + "═" * 68 + "╝")

    return "\n".join(lines)


def _generate_multi_event_schedule(tournament_state: Dict) -> str:
    """Generate combined schedule for multi-event tournament (entire day)."""
    lines = []

    # Header
    lines.append("╔" + "═" * 68 + "╗")
    lines.append("║" + "TOURNAMENT DAY SCHEDULE".center(68) + "║")
    lines.append("╠" + "═" * 68 + "╣")

    # Tournament details
    tournament_name = tournament_state.get("tournament_name", "Unknown Tournament")
    tournament_date = tournament_state.get("tournament_date", "Unknown Date")
    lines.append("║" + f"  Tournament: {tournament_name}".ljust(68) + "║")
    lines.append("║" + f"  Date: {tournament_date}".ljust(68) + "║")

    total_events = tournament_state.get("total_events", 0)
    lines.append("║" + f"  Total Events: {total_events}".ljust(68) + "║")

    lines.append("╠" + "═" * 68 + "╣")

    # Process each event
    events = tournament_state.get("events", [])
    if not events:
        lines.append("║" + "  No events configured yet".center(68) + "║")
    else:
        for idx, event in enumerate(events, 1):
            _add_event_to_schedule(lines, event, idx)

    lines.append("╚" + "═" * 68 + "╝")

    return "\n".join(lines)


def _add_event_to_schedule(lines: List[str], event: Dict, event_num: int):
    """Add an event's schedule to the lines list."""
    # Event header
    event_name = event.get("event_name", f"Event {event_num}")
    status = event.get("status", "pending")

    lines.append("║" + " " * 68 + "║")
    event_header = f"?? EVENT {event_num}: {event_name} ({status.upper()}) ??"
    lines.append("║" + event_header.center(68) + "║")

    # Event details
    wood_species = event.get("wood_species", "Unknown")
    wood_diameter = event.get("wood_diameter", 0)
    wood_quality = event.get("wood_quality", 0)
    wood_line = f"  Wood: {wood_species}, {wood_diameter}mm, Quality {wood_quality}"
    lines.append("║" + wood_line.ljust(68) + "║")

    # Rounds
    rounds = event.get("rounds", [])
    if not rounds:
        lines.append("║" + "  (Rounds not yet generated)".ljust(68) + "║")
    else:
        for round_obj in rounds:
            _add_round_to_schedule(lines, round_obj, indent=2)

    lines.append("║" + " " * 68 + "║")
    lines.append("║" + "-" * 68 + "║")


def _add_round_to_schedule(lines: List[str], round_obj: Dict, indent: int = 0):
    """Add a round's details to the schedule."""
    round_name = round_obj.get("round_name", "Unknown Round")
    competitors = round_obj.get("competitors", [])
    handicap_results = round_obj.get("handicap_results", [])
    status = round_obj.get("status", "pending")

    indent_str = " " * indent

    # Round header
    lines.append("║" + " " * 68 + "║")
    round_header = f"{indent_str}{round_name.upper()}"
    if status != "pending":
        round_header += f" [{status.upper()}]"
    lines.append("║" + f"  {round_header}".ljust(68) + "║")

    # If round not generated yet
    if not competitors:
        lines.append("║" + f"  {indent_str}(Not yet generated)".ljust(68) + "║")
        return

    # Build competitor-to-mark mapping
    comp_marks = {}
    if handicap_results:
        for entry in handicap_results:
            name = entry.get("name")
            mark = entry.get("mark", entry.get("handicap_mark", 3))
            comp_marks[name] = mark

    # Display competitors by stand
    for stand_num, comp_name in enumerate(competitors, 1):
        mark = comp_marks.get(comp_name, 3)

        # Show actual result if completed
        results_dict = round_obj.get("results", {})
        if comp_name in results_dict and results_dict[comp_name] is not None:
            actual_time = results_dict[comp_name]
            comp_line = f"  {indent_str}Stand {stand_num}: {comp_name} (Mark {mark}) - Result: {actual_time:.1f}s"
        else:
            comp_line = f"  {indent_str}Stand {stand_num}: {comp_name} (Mark {mark})"

        lines.append("║" + comp_line.ljust(68) + "║")

    # Show advancers if completed
    advancers = round_obj.get("advancers", [])
    if advancers:
        lines.append("║" + f"  {indent_str}-> Advanced: {', '.join(advancers)}".ljust(68) + "║")


def display_and_export_schedule(tournament_state: Dict):
    """
    Wrapper function to display schedule on screen and export to file.

    This is the main function to call from menu options.

    Args:
        tournament_state: Tournament state dict (single or multi-event)
    """
    print("\n" + "=" * 70)
    print("GENERATING TOURNAMENT SCHEDULE".center(70))
    print("=" * 70)

    # Generate schedule
    schedule_text = generate_printable_schedule(tournament_state)

    # Display on screen
    print("\n" + schedule_text)

    print("\n" + "=" * 70)
    print("Schedule displayed above and saved to file.".center(70))
    print("=" * 70)

    input("\nPress Enter to continue...")
