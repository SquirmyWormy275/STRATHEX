"""Improved error message display with actionable suggestions.

This module provides user-friendly error displays that:
- Clearly explain what went wrong
- Suggest specific actions to fix the issue
- Offer quick shortcuts to relevant menu options
"""

from typing import List, Optional


def display_actionable_error(
    title: str,
    message: str,
    issues: List[str] = None,
    quick_action: Optional[str] = None,
    quick_action_key: Optional[str] = None,
) -> Optional[str]:
    """Display an error message with actionable steps.

    Args:
        title: Error title (e.g., "CANNOT CALCULATE HANDICAPS")
        message: Main error message
        issues: List of specific issues/missing items
        quick_action: Description of quick action (e.g., "Calculate handicaps now")
        quick_action_key: Key to press for quick action (e.g., "5")

    Returns:
        str: User's input (quick action key or Enter)
    """
    box_width = 68

    print("\n╔" + "═" * box_width + "╗")
    print("║" + f"⚠️ {title} ⚠️".center(box_width) + "║")
    print("╠" + "═" * box_width + "╣")

    # Main message
    print("║" + message.ljust(box_width) + "║")

    # Issues list (if provided)
    if issues:
        print("║" + " " * box_width + "║")
        print("║" + "Missing or incomplete:".ljust(box_width) + "║")
        for issue in issues:
            # Wrap long issues
            if len(issue) > 66:
                issue = issue[:63] + "..."
            print("║" + f"  {issue}".ljust(box_width) + "║")

    print("╠" + "═" * box_width + "╣")

    # Action suggestions
    if quick_action and quick_action_key:
        print("║" + f"→ Press '{quick_action_key}' to {quick_action}".ljust(box_width) + "║")
        print("║" + "→ Press Enter to return to menu".ljust(box_width) + "║")
        print("╚" + "═" * box_width + "╝")

        choice = input(f"\n[{quick_action_key}/Enter]: ").strip()
        return choice
    else:
        print("║" + "Press Enter to return to menu".ljust(box_width) + "║")
        print("╚" + "═" * box_width + "╝")
        input()
        return None


def display_blocking_error(title: str, issues: List[str]) -> None:
    """Display a blocking error that prevents an operation.

    Args:
        title: Error title
        issues: List of blocking issues
    """
    box_width = 68

    print("\n╔" + "═" * box_width + "╗")
    print("║" + f"⚠️ {title} ⚠️".center(box_width) + "║")
    print("╠" + "═" * box_width + "╣")
    print("║" + "Cannot proceed due to:".ljust(box_width) + "║")
    print("║" + " " * box_width + "║")

    for issue in issues:
        # Wrap long issues
        if len(issue) > 66:
            issue = issue[:63] + "..."
        print("║" + f"  {issue}".ljust(box_width) + "║")

    print("║" + " " * box_width + "║")
    print("║" + "Please resolve these issues and try again.".ljust(box_width) + "║")
    print("╚" + "═" * box_width + "╝")
    input("\nPress Enter to continue...")


def display_warning(title: str, message: str, confirmation: bool = False) -> bool:
    """Display a warning message.

    Args:
        title: Warning title
        message: Warning message
        confirmation: If True, ask for y/n confirmation

    Returns:
        bool: True if user confirms (or no confirmation needed), False otherwise
    """
    box_width = 68

    print("\n╔" + "═" * box_width + "╗")
    print("║" + f"⚠️ {title}".center(box_width) + "║")
    print("╠" + "═" * box_width + "╣")
    print("║" + message.ljust(box_width) + "║")

    if confirmation:
        print("╠" + "═" * box_width + "╣")
        print("║" + "Do you want to proceed? (y/n)".ljust(box_width) + "║")
        print("╚" + "═" * box_width + "╝")

        choice = input("\n[y/n]: ").strip().lower()
        return choice == "y"
    else:
        print("╚" + "═" * box_width + "╝")
        input("\nPress Enter to continue...")
        return True


def display_success(message: str, details: List[str] = None) -> None:
    """Display a success message.

    Args:
        message: Success message
        details: Optional list of detail lines
    """
    box_width = 68

    print("\n╔" + "═" * box_width + "╗")
    print("║" + f"✓ {message}".center(box_width) + "║")

    if details:
        print("╠" + "═" * box_width + "╣")
        for detail in details:
            if len(detail) > 66:
                detail = detail[:63] + "..."
            print("║" + f"  {detail}".ljust(box_width) + "║")

    print("╚" + "═" * box_width + "╝")
    input("\nPress Enter to continue...")


def display_progress_box(title: str, current: int, total: int, item_name: str = "items") -> None:
    """Display a progress box for batch operations.

    Args:
        title: Operation title
        current: Current item number
        total: Total items
        item_name: Name of items being processed (e.g., "competitors", "events")
    """
    box_width = 68
    percent = int((current / total) * 100) if total > 0 else 0
    bar_length = 40
    filled = int((bar_length * current) / total) if total > 0 else 0
    bar = "█" * filled + "░" * (bar_length - filled)

    print("\n╔" + "═" * box_width + "╗")
    print("║" + title.center(box_width) + "║")
    print("╠" + "═" * box_width + "╣")
    print("║" + " " * box_width + "║")
    print("║" + f"  [{bar}] {percent:3d}%".ljust(box_width) + "║")
    print("║" + f"  Progress: {current}/{total} {item_name}".ljust(box_width) + "║")
    print("║" + " " * box_width + "║")
    print("╚" + "═" * box_width + "╝")


def prompt_with_options(
    question: str,
    options: List[tuple],  # List of (key, description) tuples
    allow_cancel: bool = True,
) -> Optional[str]:
    """Display a menu of options and get user choice.

    Args:
        question: Question to ask
        options: List of (key, description) tuples
        allow_cancel: If True, allow canceling with Enter

    Returns:
        str: Selected option key, or None if cancelled
    """
    box_width = 68

    print("\n╔" + "═" * box_width + "╗")
    print("║" + question.center(box_width) + "║")
    print("╠" + "═" * box_width + "╣")

    for key, description in options:
        line = f"  {key}. {description}"
        if len(line) > 66:
            line = line[:63] + "..."
        print("║" + line.ljust(box_width) + "║")

    if allow_cancel:
        print("║" + " " * box_width + "║")
        print("║" + "  Press Enter to cancel".ljust(box_width) + "║")

    print("╚" + "═" * box_width + "╝")

    valid_keys = [k for k, _ in options]
    prompt_text = f"[{'/'.join(valid_keys)}" + ("/Enter" if allow_cancel else "") + "]: "

    choice = input(f"\n{prompt_text}").strip()

    if choice == "" and allow_cancel:
        return None

    if choice in valid_keys:
        return choice

    print("\n⚠️ Invalid choice")
    return None
