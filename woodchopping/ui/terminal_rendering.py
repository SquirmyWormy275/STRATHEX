"""Terminal-safe rendering helpers for STRATHEX's judge-facing CLI.

The application deliberately keeps a retro text interface. These helpers make
that interface deterministic across Windows consoles and terminals whose
character cells do not match Python's ``len()`` semantics.

Functional text is converted to conservative ASCII. The approved box-drawing
characters are retained, but box interiors and known animations are fitted by
terminal display width rather than Unicode code-point count.
"""

from __future__ import annotations

import re
import sys
import unicodedata
from typing import TextIO

APPROVED_BOX_CHARACTERS = frozenset("╔╗╚╝╠╣║═")
_ZERO_WIDTH_CHARACTERS = frozenset({"\u200b", "\u200c", "\u200d", "\ufeff", "\ufe0e", "\ufe0f"})
_ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
_SLOT_LINE_RE = re.compile(r"^\s*\[\s*(.*?)\s*\]\s+\[\s*(.*?)\s*\]\s+\[\s*(.*?)\s*\]\s*$")
_ASCII_BOX_BORDER_RE = re.compile(r"^\+([=\-])+\+$")

_SYMBOL_REPLACEMENTS = {
    "⚠": "[WARN]",
    "✅": "[OK]",
    "☑": "[OK]",
    "✓": "[OK]",
    "✔": "[OK]",
    "❌": "[X]",
    "✗": "[X]",
    "✘": "[X]",
    "❎": "[X]",
    "🪓": "AXE",
    "🏆": "WINNER",
    "🥇": "1ST",
    "🥈": "2ND",
    "🥉": "3RD",
    "→": "->",
    "➜": "->",
    "➔": "->",
    "⇒": "=>",
    "←": "<-",
    "↑": "^",
    "↓": "v",
    "•": "-",
    "·": "-",
    "—": "-",
    "–": "-",
    "−": "-",
    "…": "...",
    "±": "+/-",
    "×": "x",
    "≥": ">=",
    "≤": "<=",
    "≠": "!=",
    "█": "#",
    "▓": "#",
    "▒": "#",
    "░": ".",
    "●": "*",
    "○": "o",
    "◆": "*",
    "◇": "o",
}


def sanitize_text(value: object) -> str:
    """Return terminal-safe text without changing ordinary names or wording."""
    text = "" if value is None else str(value)
    text = _ANSI_ESCAPE_RE.sub("", text)

    output: list[str] = []
    for character in text:
        if character in _ZERO_WIDTH_CHARACTERS:
            continue
        replacement = _SYMBOL_REPLACEMENTS.get(character)
        if replacement is not None:
            output.append(replacement)
            continue

        # Retain the small approved box alphabet. Strip other decorative
        # symbols that have no stable width in legacy Windows consoles.
        if character in APPROVED_BOX_CHARACTERS:
            output.append(character)
            continue
        if unicodedata.category(character) == "So":
            continue

        output.append(character)

    return "".join(output)


def character_width(character: str) -> int:
    """Return the number of terminal cells occupied by one Unicode character."""
    if not character or character in _ZERO_WIDTH_CHARACTERS:
        return 0
    if character == "\t":
        return 4
    if character in "\r\n":
        return 0
    if unicodedata.combining(character):
        return 0
    category = unicodedata.category(character)
    if category in {"Cc", "Cf"}:
        return 0
    return 2 if unicodedata.east_asian_width(character) in {"W", "F"} else 1


def display_width(value: object) -> int:
    """Measure terminal-cell width after removing ANSI control sequences."""
    text = _ANSI_ESCAPE_RE.sub("", "" if value is None else str(value))
    return sum(character_width(character) for character in text)


def truncate_display(value: object, width: int, ellipsis: str = "...") -> str:
    """Truncate text to at most ``width`` terminal cells."""
    width = max(0, int(width))
    text = "" if value is None else str(value)
    if display_width(text) <= width:
        return text
    if width == 0:
        return ""

    ellipsis = str(ellipsis)
    ellipsis_width = display_width(ellipsis)
    if ellipsis_width >= width:
        ellipsis = ""
        ellipsis_width = 0

    target = width - ellipsis_width
    output: list[str] = []
    used = 0
    for character in text:
        char_width = character_width(character)
        if used + char_width > target:
            break
        output.append(character)
        used += char_width
    return "".join(output) + ellipsis


def fit_display(value: object, width: int, align: str = "left") -> str:
    """Truncate and pad text to exactly ``width`` terminal cells."""
    width = max(0, int(width))
    text = truncate_display(value, width)
    remaining = max(0, width - display_width(text))

    if align == "right":
        return " " * remaining + text
    if align == "center":
        left = remaining // 2
        return " " * left + text + " " * (remaining - left)
    return text + " " * remaining


def _normalize_separator(line: str, width: int = 70) -> str:
    stripped = line.strip()
    if not stripped or display_width(stripped) < 58 or display_width(stripped) > 82:
        return line
    if len(set(stripped)) == 1 and stripped[0] in {"=", "-", "_", "═"}:
        return stripped[0] * width
    if _ASCII_BOX_BORDER_RE.fullmatch(stripped):
        fill = stripped[1]
        return "+" + fill * (width - 2) + "+"
    return line


def _normalize_box_line(line: str, width: int = 70) -> str:
    if width < 4:
        return line

    pairs = {
        ("╔", "╗"),
        ("╠", "╣"),
        ("╚", "╝"),
        ("║", "║"),
        ("|", "|"),
    }
    if len(line) < 2 or (line[0], line[-1]) not in pairs:
        return line

    # Do not rewrite wide multi-column ASCII tables.
    if line[0] == "|":
        if line.count("|") != 2:
            return line
        if not 58 <= display_width(line) <= 82:
            return line

    inner_width = width - 2
    inner = line[1:-1]

    if line[0] in {"╔", "╠", "╚"}:
        return line[0] + "═" * inner_width + line[-1]

    if not inner.strip():
        return line[0] + " " * inner_width + line[-1]

    left_spaces = len(inner) - len(inner.lstrip(" "))
    right_spaces = len(inner) - len(inner.rstrip(" "))
    centered_or_right_content = inner.strip(" ")
    left_content = inner.rstrip(" ")

    if left_spaces and right_spaces and abs(left_spaces - right_spaces) <= 6:
        align = "center"
        content = centered_or_right_content
    elif left_spaces > right_spaces * 2:
        align = "right"
        content = centered_or_right_content
    else:
        align = "left"
        content = left_content

    return line[0] + fit_display(content, inner_width, align=align) + line[-1]


def _normalize_slot_line(line: str, field_width: int = 18) -> str:
    match = _SLOT_LINE_RE.fullmatch(line)
    if not match:
        return line

    fields = [fit_display(field, field_width) for field in match.groups()]
    return f"  [ {fields[0]} ] [ {fields[1]} ] [ {fields[2]} ]"


def normalize_terminal_line(value: object, width: int = 70) -> str:
    """Sanitize and align one complete terminal line."""
    line = sanitize_text(value)
    line = _normalize_slot_line(line)
    line = _normalize_box_line(line, width=width)
    line = _normalize_separator(line, width=width)

    if line.strip() == "SLOT MACHINE DRAW":
        line = fit_display(line.strip(), width, align="center")
    return line


class TerminalOutput:
    """Line-buffering proxy that normalizes text before writing it."""

    def __init__(self, stream: TextIO, width: int = 70) -> None:
        self._stream = stream
        self._width = int(width)
        self._buffer = ""

    @property
    def encoding(self):
        return getattr(self._stream, "encoding", "utf-8")

    @property
    def errors(self):
        return getattr(self._stream, "errors", None)

    def writable(self) -> bool:
        return True

    def isatty(self) -> bool:
        return bool(getattr(self._stream, "isatty", lambda: False)())

    def fileno(self) -> int:
        return self._stream.fileno()

    def write(self, text: str) -> int:
        incoming = "" if text is None else str(text)
        self._buffer += incoming

        while True:
            match = re.search(r"\r\n|\n|\r", self._buffer)
            if match is None:
                break
            line = self._buffer[: match.start()]
            separator = match.group(0)
            self._buffer = self._buffer[match.end() :]
            self._stream.write(normalize_terminal_line(line, width=self._width))
            self._stream.write(separator)

        return len(incoming)

    def flush(self) -> None:
        if self._buffer:
            # Prompts and incremental status text deliberately have no newline.
            # Sanitize them, but do not impose a fixed line width.
            self._stream.write(sanitize_text(self._buffer))
            self._buffer = ""
        self._stream.flush()

    def __getattr__(self, name: str):
        return getattr(self._stream, name)


def install_terminal_output(
    *,
    width: int = 70,
    force: bool = False,
    include_stderr: bool = False,
) -> bool:
    """Install the output proxy once for an interactive STRATHEX session."""
    if isinstance(sys.stdout, TerminalOutput):
        return False
    if not force and not sys.stdout.isatty():
        return False

    sys.stdout = TerminalOutput(sys.stdout, width=width)
    if include_stderr and not isinstance(sys.stderr, TerminalOutput):
        sys.stderr = TerminalOutput(sys.stderr, width=width)
    return True
