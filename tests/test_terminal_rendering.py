"""Regression tests for terminal graphics and animation alignment."""

from __future__ import annotations

import io

from woodchopping.ui.progress_ui import ProgressDisplay
from woodchopping.ui.terminal_rendering import (
    TerminalOutput,
    display_width,
    fit_display,
    normalize_terminal_line,
    sanitize_text,
)


def test_warning_banner_is_exactly_seventy_cells_wide():
    raw = "║" + "⚠️ CANNOT CALCULATE HANDICAPS ⚠️".center(68) + "║"

    rendered = normalize_terminal_line(raw)

    assert display_width(rendered) == 70
    assert rendered.startswith("║") and rendered.endswith("║")
    assert "[WARN] CANNOT CALCULATE HANDICAPS [WARN]" in rendered


def test_box_content_keeps_functional_left_indentation():
    raw = "║" + "  ? Tournament not configured".ljust(68) + "║"

    rendered = normalize_terminal_line(raw)

    assert display_width(rendered) == 70
    assert rendered.startswith("║  ? Tournament")


def test_slot_machine_fields_align_with_wide_and_accented_names():
    raw = f"  [ {'Alice'.ljust(18)} ] [ {'山田太郎'.ljust(18)} ] [ {'José'.ljust(18)} ]"

    rendered = normalize_terminal_line(raw)

    assert display_width(rendered) == 70
    assert rendered.count("[") == 3
    assert "山田太郎" in rendered
    assert "José" in rendered


def test_near_seventy_character_separators_use_one_geometry():
    assert normalize_terminal_line("=" * 64) == "=" * 70
    assert normalize_terminal_line("-" * 68) == "-" * 70


def test_functional_decorations_have_ascii_fallbacks():
    rendered = sanitize_text("✅ Ready → next round; ±3s; ███")

    assert rendered == "[OK] Ready -> next round; +/-3s; ###"


def test_terminal_output_normalizes_carriage_return_animation_frames():
    target = io.StringIO()
    output = TerminalOutput(target, width=70)

    output.write("  [ Alice ] [ 山田太郎 ] [ José ]\r")
    output.flush()

    rendered, separator = target.getvalue()[:-1], target.getvalue()[-1]
    assert separator == "\r"
    assert display_width(rendered) == 70


def test_fit_display_uses_terminal_cells_not_python_length():
    rendered = fit_display("山田", 8, align="center")

    assert display_width(rendered) == 8
    assert rendered.strip() == "山田"


def test_progress_display_lines_never_exceed_configured_width(capsys):
    progress = ProgressDisplay(
        title="⚠️ HANDICAP CALCULATION IN PROGRESS ⚠️",
        width=70,
        bar_length=40,
        item_label="competitors",
        detail_label="Analyzing",
    )

    progress.start()
    progress.update(1, 10, "山田太郎 with an intentionally long description")
    progress.finish("✅ All competitors analyzed successfully!")

    lines = [line for line in capsys.readouterr().out.splitlines() if line]
    assert lines
    assert all(display_width(line) == 70 for line in lines)
    assert all("⚠" not in line and "✅" not in line for line in lines)
