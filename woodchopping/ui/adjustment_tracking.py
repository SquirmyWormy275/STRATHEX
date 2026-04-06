"""
Handicap Override Tracker (A5)

Tracks all manual handicap adjustments with full audit trail.
Helps judges understand why adjustments were made and builds institutional knowledge.
"""

from datetime import datetime
from typing import Dict, List


def log_handicap_adjustment(
    tournament_state: Dict,
    competitor_name: str,
    original_mark: int,
    adjusted_mark: int,
    reason: str = "",
    adjustment_type: str = "manual",
) -> None:
    """
    Log a handicap adjustment to the tournament state.

    Args:
        tournament_state: Tournament state dict to update
        competitor_name: Name of the competitor
        original_mark: Original predicted mark
        adjusted_mark: Adjusted mark (after judge modification)
        reason: Explanation for the adjustment
        adjustment_type: Type of adjustment ("manual" or "automatic")
    """
    # Initialize adjustment_log if it doesn't exist
    if "adjustment_log" not in tournament_state:
        tournament_state["adjustment_log"] = []

    # Create adjustment record
    adjustment_record = {
        "competitor": competitor_name,
        "event": tournament_state.get("event_name", "Unknown Event"),
        "original_mark": original_mark,
        "adjusted_mark": adjusted_mark,
        "change": adjusted_mark - original_mark,
        "reason": reason if reason else "No reason provided",
        "adjustment_type": adjustment_type,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }

    tournament_state["adjustment_log"].append(adjustment_record)


def prompt_adjustment_reason() -> str:
    """
    Prompt judge to enter reason for handicap adjustment.

    Returns:
        Reason string entered by judge
    """
    print("\n" + "-" * 70)
    print("ADJUSTMENT REASON (Required for Audit Trail)".center(70))
    print("-" * 70)
    print("Please explain why you're adjusting this handicap.")
    print("Examples:")
    print("  - Wood quality worse than expected")
    print("  - Competitor recently injured")
    print("  - Based on performance in earlier round")
    print("  - Diameter measurement was incorrect")
    print()

    reason = input("Reason for adjustment: ").strip()

    while not reason:
        print("[WARN] Reason is required for audit trail.")
        reason = input("Reason for adjustment: ").strip()

    return reason


def view_adjustment_history(tournament_state: Dict) -> None:
    """
    Display all handicap adjustments made in this tournament.

    Args:
        tournament_state: Tournament state dict
    """
    print("\n╔" + "═" * 68 + "╗")
    print("║" + "HANDICAP ADJUSTMENT HISTORY".center(68) + "║")
    print("╚" + "═" * 68 + "╝\n")

    adjustment_log = tournament_state.get("adjustment_log", [])

    if not adjustment_log:
        print("No manual adjustments have been made.")
        print("All handicaps were accepted as calculated by the system.\n")
        input("Press Enter to continue...")
        return

    # Display summary statistics
    total_adjustments = len(adjustment_log)
    manual_adjustments = [a for a in adjustment_log if a.get("adjustment_type") == "manual"]
    auto_adjustments = [a for a in adjustment_log if a.get("adjustment_type") == "automatic"]

    changes = [abs(a["change"]) for a in adjustment_log]
    avg_change = sum(changes) / len(changes) if changes else 0

    print(f"Total Adjustments: {total_adjustments}")
    print(f"  Manual: {len(manual_adjustments)}")
    print(f"  Automatic (recalculations): {len(auto_adjustments)}")
    print(f"Average Magnitude: {avg_change:.1f} seconds\n")

    print("-" * 70)

    # Display adjustment table
    print("+" + "-" * 20 + "+" + "-" * 10 + "+" + "-" * 10 + "+" + "-" * 9 + "+" + "-" * 14 + "+")
    print("| Competitor         | Original | Adjusted | Change  | Type         |")
    print("+" + "-" * 20 + "+" + "-" * 10 + "+" + "-" * 10 + "+" + "-" * 9 + "+" + "-" * 14 + "+")

    for adj in adjustment_log:
        name = adj["competitor"][:18].ljust(18)
        original = str(adj["original_mark"]).center(8)
        adjusted = str(adj["adjusted_mark"]).center(8)
        change_val = adj["change"]
        change_str = f"{change_val:+d}".center(7)
        adj_type = adj.get("adjustment_type", "manual")[:12].ljust(12)

        print(f"| {name} | {original} | {adjusted} | {change_str} | {adj_type} |")

        # Show reason on next line
        reason = adj.get("reason", "No reason provided")
        # Word wrap reason to fit in 66 characters
        reason_lines = _word_wrap(reason, 66)
        for line in reason_lines:
            print(f"|   -> {line}".ljust(69) + "|")

        print("+" + "-" * 20 + "+" + "-" * 10 + "+" + "-" * 10 + "+" + "-" * 9 + "+" + "-" * 14 + "+")

    print("+" + "-" * 20 + "+" + "-" * 10 + "+" + "-" * 10 + "+" + "-" * 9 + "+" + "-" * 14 + "+")

    print("\n" + "-" * 70)
    input("\nPress Enter to continue...")


def get_adjustment_summary(tournament_state: Dict) -> str:
    """
    Get a summary of adjustments for inclusion in reports.

    Args:
        tournament_state: Tournament state dict

    Returns:
        Formatted summary string
    """
    adjustment_log = tournament_state.get("adjustment_log", [])

    if not adjustment_log:
        return "No manual handicap adjustments were made."

    total = len(adjustment_log)
    manual = len([a for a in adjustment_log if a.get("adjustment_type") == "manual"])
    auto = len([a for a in adjustment_log if a.get("adjustment_type") == "automatic"])

    changes = [abs(a["change"]) for a in adjustment_log]
    avg_change = sum(changes) / len(changes) if changes else 0

    summary = f"Handicap Adjustments: {total} total ({manual} manual, {auto} automatic)\n"
    summary += f"Average adjustment magnitude: {avg_change:.1f} seconds"

    return summary


def _word_wrap(text: str, width: int) -> List[str]:
    """
    Simple word wrap function.

    Args:
        text: Text to wrap
        width: Maximum width per line

    Returns:
        List of wrapped lines
    """
    if len(text) <= width:
        return [text]

    lines = []
    words = text.split()
    current_line = ""

    for word in words:
        if len(current_line) + len(word) + 1 <= width:
            current_line += (" " + word) if current_line else word
        else:
            if current_line:
                lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    return lines
