"""Render shared STRATHEX terminal primitives for manual Windows checks.

Run from the repository root:
    python scripts/terminal_gallery.py
    python scripts/terminal_gallery.py --capture terminal-gallery.txt
"""

from __future__ import annotations

import argparse
import contextlib
import io
import sys
from pathlib import Path

from woodchopping.ui.error_display import display_progress_box
from woodchopping.ui.progress_ui import ProgressDisplay
from woodchopping.ui.terminal_rendering import TerminalOutput


def render_gallery() -> str:
    """Return one normalized sample of the principal terminal geometries."""
    target = io.StringIO()
    terminal = TerminalOutput(target, width=70)
    with contextlib.redirect_stdout(terminal):
        print("STRATHEX TERMINAL GALLERY")
        print("=" * 70)
        print("╔" + "═" * 68 + "╗")
        print("║" + "⚠️ STARTUP / STATUS ⚠️".center(68) + "║")
        print("║" + "  ✅ Workbook loaded → next round".ljust(68) + "║")
        print("║" + "  Alexandria Montgomery-Smith | José Álvarez | 山田太郎".ljust(68) + "║")
        print("╚" + "═" * 68 + "╝")
        print(f"  [ {'Alice'.ljust(18)} ] [ {'山田太郎'.ljust(18)} ] [ {'José'.ljust(18)} ]")
        display_progress_box("BATCH CALCULATION", 5, 10, "competitors")
        progress = ProgressDisplay(
            title="⚠️ HANDICAP CALCULATION IN PROGRESS ⚠️",
            width=70,
            bar_length=40,
            item_label="competitors",
            detail_label="Analyzing",
        )
        progress.start()
        progress.update(1, 2, "山田太郎 with a deliberately long status line")
        progress.finish("✅ Gallery complete")
    terminal.flush()
    return target.getvalue()


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    parser = argparse.ArgumentParser(description="Render STRATHEX's shared terminal UI primitives.")
    parser.add_argument("--capture", type=Path, help="Optional plain-text capture path.")
    args = parser.parse_args()
    rendered = render_gallery()
    print(rendered, end="")
    if args.capture:
        args.capture.write_text(rendered, encoding="utf-8")
        print(f"\nCaptured gallery to {args.capture}")


if __name__ == "__main__":
    main()
