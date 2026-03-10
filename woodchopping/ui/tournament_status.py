# -*- coding: utf-8 -*-
"""Tournament status tracking and progress visualization.

This module provides:
- Progress tracker dashboard for multi-event tournaments
- Status calculation and validation
- Visual progress indicators
"""

from typing import Dict, List, Tuple, Optional


def calculate_tournament_progress(tournament_state: Dict) -> Dict:
    """Calculate completion status for all tournament phases.

    Args:
        tournament_state: Multi-event tournament state

    Returns:
        dict: Progress data with completion flags and percentages
    """
    progress = {
        'tournament_created': bool(tournament_state.get('tournament_name')),
        'events_defined': False,
        'events_count': 0,
        'roster_configured': False,
        'roster_count': 0,
        'assignments_complete': False,
        'assignments_count': 0,
        'assignments_total': 0,
        'handicaps_calculated': False,
        'handicaps_count': 0,
        'schedule_generated': False,
        'competition_started': False,
        'competition_complete': False,
        'completed_events': 0,
        'unpaid_fees_count': 0,
        'next_step': '',
        'blocking_issues': []
    }

    # Events defined
    events = tournament_state.get('events', [])
    progress['events_count'] = len(events)
    progress['events_defined'] = len(events) > 0

    # Roster configured
    roster = tournament_state.get('tournament_roster', [])
    progress['roster_count'] = len(roster)
    progress['roster_configured'] = len(roster) > 0

    # Assignment tracking
    if roster:
        assigned_competitors = sum(1 for comp in roster if comp.get('events_entered'))
        progress['assignments_count'] = assigned_competitors
        progress['assignments_total'] = len(roster)
        progress['assignments_complete'] = (assigned_competitors == len(roster))

    # Handicaps calculated
    if events:
        ready_events = [e for e in events if e.get('status') in ['ready', 'scheduled', 'in_progress', 'completed']]
        progress['handicaps_count'] = len(ready_events)
        progress['handicaps_calculated'] = (len(ready_events) == len(events))

    # Schedule generated
    if events:
        scheduled_events = [e for e in events if e.get('rounds')]
        progress['schedule_generated'] = len(scheduled_events) > 0

    # Competition tracking
    if events:
        started_events = [e for e in events if e.get('status') in ['in_progress', 'completed']]
        progress['competition_started'] = len(started_events) > 0

        completed_events = [e for e in events if e.get('status') == 'completed']
        progress['completed_events'] = len(completed_events)
        progress['competition_complete'] = (len(completed_events) == len(events))

    # Entry fee tracking
    if tournament_state.get('entry_fee_tracking_enabled'):
        unpaid_count = 0
        for comp in roster:
            for event_id, paid in comp.get('entry_fees_paid', {}).items():
                if not paid:
                    unpaid_count += 1
        progress['unpaid_fees_count'] = unpaid_count

    # Scratch tracking
    scratched_count = sum(1 for c in roster if c.get('status') == 'scratched')
    progress['scratched_count'] = scratched_count

    # Determine next step
    progress['next_step'] = determine_next_step(progress, tournament_state)

    # Identify blocking issues
    progress['blocking_issues'] = identify_blocking_issues(progress, tournament_state)

    return progress


def determine_next_step(progress: Dict, tournament_state: Dict) -> str:
    """Determine what the judge should do next.

    Args:
        progress: Progress data from calculate_tournament_progress
        tournament_state: Multi-event tournament state

    Returns:
        str: Human-readable next step description
    """
    if not progress['tournament_created']:
        return "Create a new tournament (Option 1)"

    if not progress['events_defined']:
        return "Add events to tournament (Option 2)"

    if not progress['roster_configured']:
        return "Setup tournament roster (Option 3)"

    if not progress['assignments_complete']:
        remaining = progress['assignments_total'] - progress['assignments_count']
        return f"Complete event assignments ({remaining} competitors remaining) (Option 4)"

    if not progress['handicaps_calculated']:
        remaining = progress['events_count'] - progress['handicaps_count']
        return f"Calculate handicaps for all events ({remaining} events pending) (Option 7)"

    if not progress['schedule_generated']:
        return "Generate complete day schedule (Option 10)"

    if not progress['competition_started']:
        return "Begin competition - Sequential results entry (Option 11)"

    if not progress['competition_complete']:
        remaining = progress['events_count'] - progress['completed_events']
        return f"Continue recording results ({remaining} events remaining) (Option 11)"

    return "Generate final tournament summary (Option 14)"


def identify_blocking_issues(progress: Dict, tournament_state: Dict) -> List[str]:
    """Identify issues that block tournament progression.

    Args:
        progress: Progress data from calculate_tournament_progress
        tournament_state: Multi-event tournament state

    Returns:
        list: List of issue descriptions
    """
    issues = []

    # Check for events with insufficient competitors
    events = tournament_state.get('events', [])
    for event in events:
        comp_count = len(event.get('all_competitors', []))
        if comp_count == 1:
            issues.append(f"[WARN] {event['event_name']} has only 1 competitor (need min 2)")
        elif comp_count == 0 and event.get('status') != 'pending':
            issues.append(f"[WARN] {event['event_name']} has no competitors assigned")

    # Check for unpaid fees (warning, not blocking)
    if progress['unpaid_fees_count'] > 0:
        issues.append(f"[WARN] {progress['unpaid_fees_count']} unpaid entry fees")

    # Check for competitors not assigned to any events
    roster = tournament_state.get('tournament_roster', [])
    unassigned = [comp for comp in roster if not comp.get('events_entered')]
    if unassigned:
        issues.append(f"[WARN] {len(unassigned)} competitors not assigned to any events")

    return issues


def display_tournament_progress_tracker(tournament_state: Dict) -> None:
    """Display visual progress tracker dashboard at top of menu.

    Shows:
    - Tournament name and date
    - Completion status for each phase
    - Next recommended action
    - Blocking issues (if any)

    Args:
        tournament_state: Multi-event tournament state
    """
    progress = calculate_tournament_progress(tournament_state)

    tournament_name = tournament_state.get('tournament_name', 'Unnamed Tournament')
    tournament_date = tournament_state.get('tournament_date', 'Date not set')

    # Build status display
    print("\n╔" + "═" * 68 + "╗")
    print("║" + tournament_name.center(68) + "║")
    print("║" + tournament_date.center(68) + "║")
    print("╠" + "═" * 68 + "╣")
    print("║" + "  TOURNAMENT STATUS".ljust(68) + "║")
    print("║" + " " * 68 + "║")

    # Phase status lines
    status_lines = [
        ("Tournament Created", progress['tournament_created'], ""),
        ("Events Defined", progress['events_defined'], f"({progress['events_count']} events)"),
        ("Roster Configured", progress['roster_configured'], f"({progress['roster_count']} competitors)"),
        ("Event Assignment", progress['assignments_complete'],
         f"({progress['assignments_count']}/{progress['assignments_total']} assigned)"),
        ("Handicaps Calculated", progress['handicaps_calculated'],
         f"({progress['handicaps_count']}/{progress['events_count']} events)"),
        ("Schedule Generated", progress['schedule_generated'], ""),
        ("Competition Started", progress['competition_started'], ""),
    ]

    for label, complete, detail in status_lines:
        if complete:
            icon = "[✓]"
        elif detail and "/" in detail:
            # Partial completion
            icon = "[~]"
        else:
            icon = "[ ]"

        line = f"  {icon} {label}"
        if detail:
            line = f"{line} {detail}"

        print("║" + line.ljust(68) + "║")

    # Competition progress (if started)
    if progress['competition_started']:
        comp_line = f"  Progress: {progress['completed_events']}/{progress['events_count']} events completed"
        print("║" + comp_line.ljust(68) + "║")

    print("║" + " " * 68 + "║")

    # Next step
    next_step = f"  NEXT STEP: {progress['next_step']}"
    # Wrap if too long (allow up to 66 chars)
    if len(next_step) > 68:
        # Split into multiple lines
        words = next_step.split()
        line = ""
        for word in words:
            if len(line + " " + word) <= 66:
                line += (" " + word if line else word)
            else:
                print("║" + line.ljust(68) + "║")
                line = "  " + word
        if line:
            print("║" + line.ljust(68) + "║")
    else:
        print("║" + next_step.ljust(68) + "║")

    # Blocking issues
    if progress['blocking_issues']:
        print("║" + " " * 68 + "║")
        print("║" + "  ISSUES:".ljust(68) + "║")
        for issue in progress['blocking_issues']:
            # Truncate if too long
            if len(issue) > 66:
                issue = issue[:63] + "..."
            print("║" + f"  {issue}".ljust(68) + "║")

    # Show scratch/unpaid fee info if any
    if progress.get('scratched_count', 0) > 0 or progress.get('unpaid_fees_count', 0) > 0:
        print("║" + " " * 68 + "║")
        if progress.get('scratched_count', 0) > 0:
            scratch_line = f"  ⚠️ {progress['scratched_count']} competitor(s) scratched"
            print("║" + scratch_line.ljust(68) + "║")
        if progress.get('unpaid_fees_count', 0) > 0:
            fee_line = f"  ⚠️ {progress['unpaid_fees_count']} unpaid entry fees"
            print("║" + fee_line.ljust(68) + "║")

    print("╚" + "═" * 68 + "╝")


def get_progress_summary(tournament_state: Dict) -> str:
    """Get one-line progress summary for compact displays.

    Args:
        tournament_state: Multi-event tournament state

    Returns:
        str: One-line summary (e.g., "5/8 events completed, 23 competitors")
    """
    progress = calculate_tournament_progress(tournament_state)

    if progress['competition_complete']:
        return f"Tournament complete - {progress['events_count']} events, {progress['roster_count']} competitors"
    elif progress['competition_started']:
        return f"{progress['completed_events']}/{progress['events_count']} events completed"
    elif progress['schedule_generated']:
        return f"Schedule ready - {progress['events_count']} events, {progress['roster_count']} competitors"
    elif progress['handicaps_calculated']:
        return f"Handicaps ready - {progress['events_count']} events"
    elif progress['assignments_complete']:
        return f"Assignments complete - {progress['roster_count']} competitors"
    elif progress['roster_configured']:
        return f"Roster ready - {progress['roster_count']} competitors"
    elif progress['events_defined']:
        return f"{progress['events_count']} events defined"
    else:
        return "Tournament created - not configured"


def check_can_calculate_handicaps(tournament_state: Dict) -> Tuple[bool, List[str]]:
    """Validate that handicaps can be calculated for all events.

    Args:
        tournament_state: Multi-event tournament state

    Returns:
        tuple: (can_proceed, list of error messages)
    """
    errors = []
    events = tournament_state.get('events', [])

    if not events:
        errors.append("No events in tournament")
        return False, errors

    for event in events:
        event_name = event.get('event_name', 'Unknown Event')

        # Skip if already calculated
        if event.get('status') in ['ready', 'scheduled', 'in_progress', 'completed']:
            continue

        # Check event type - championship events don't need handicap calculation
        if event.get('event_type') == 'championship':
            continue

        # Check wood configuration
        if not event.get('wood_species'):
            errors.append(f"{event_name}: Wood species not configured")
        if not event.get('wood_diameter'):
            errors.append(f"{event_name}: Wood diameter not configured")
        if event.get('wood_quality') is None:
            errors.append(f"{event_name}: Wood quality not configured")
        if not event.get('event_code'):
            errors.append(f"{event_name}: Event code not set")

        # Check competitors
        competitors = event.get('all_competitors', [])
        if len(competitors) == 0:
            errors.append(f"{event_name}: No competitors assigned")
        elif len(competitors) == 1:
            errors.append(f"{event_name}: Only 1 competitor (need minimum 2)")

    can_proceed = (len(errors) == 0)
    return can_proceed, errors


def check_can_generate_schedule(tournament_state: Dict) -> Tuple[bool, List[str]]:
    """Validate that schedule can be generated for all events.

    Args:
        tournament_state: Multi-event tournament state

    Returns:
        tuple: (can_proceed, list of error messages)
    """
    errors = []
    events = tournament_state.get('events', [])

    if not events:
        errors.append("No events in tournament")
        return False, errors

    for event in events:
        event_name = event.get('event_name', 'Unknown Event')

        # Skip if already scheduled
        if event.get('rounds'):
            continue

        # Check status
        status = event.get('status', 'pending')
        if status not in ['ready', 'scheduled']:
            errors.append(f"{event_name}: Handicaps not calculated (status: {status})")

        # Check format configured
        if not event.get('format'):
            errors.append(f"{event_name}: Tournament format not configured")
        if not event.get('num_stands'):
            errors.append(f"{event_name}: Number of stands not configured")

        # Check competitors
        competitors = event.get('all_competitors', [])
        if len(competitors) < 2:
            errors.append(f"{event_name}: Need at least 2 competitors")

    can_proceed = (len(errors) == 0)
    return can_proceed, errors
