---
title: Windows terminals render non-ASCII characters as mojibake — use plain ASCII for functional text, box-drawing only in approved banners
date: 2026-04-21
category: runtime-errors
module: ui
problem_type: runtime_error
component: tooling
symptoms:
  - "Tournament results screen shows garbled `?` or scrambled glyphs where box-drawing, arrows, or emojis were intended"
  - "'ADVANCES' text rendered as trophy/medal glyphs that display as mojibake"
  - "Judge sees corrupted output at the most critical moment of a live tournament"
  - "Problem recurs after each 'cleanup' because different sessions touch different files"
root_cause: config_error
resolution_type: code_fix
severity: high
related_components:
  - development_workflow
tags: [unicode, ascii, windows, terminal, cp1252, utf-8, judge-ui]
---

# Windows terminals render non-ASCII characters as mojibake — use plain ASCII for functional text, box-drawing only in approved banners

## Problem
STRATHEX runs in Windows PowerShell and cmd.exe as its primary judge-facing environment. Both terminals default to CP-1252, not UTF-8. Any non-ASCII character in the UI — box-drawing glyphs (╔╗╚╝║═), arrows (→↑), emojis, checkmarks (✓), medals (🥇) — renders as mojibake on unconfigured Windows systems. The system was originally developed with UTF-8-capable terminals where the bug was invisible.

The issue has recurred twice: once in V5.2.1 (commit `18292c5`, 2026-01-24, "Reorganize files and fixed UNICODE/ASCII issues") and again three days later in V5.2.1's follow-up (commit `4cb372b`, "Critical Bugs fixed and file structures cleaned"). Both cleanups were partial — they fixed the files each session touched but missed files that were not currently being edited. Then the user opened a session with the quote: "Hey! I thought you said that you cleaned up the ASCII art!!!"

## Symptoms
- `?` characters in the middle of otherwise correct text
- Scrambled two-byte sequences like `â–ˆ` or `Ã¢â€"â€"` where box-drawing was intended
- Banners that look aligned in the editor but broken in the terminal
- Appears only on certain Windows configurations — easy to miss in development
- Recurs whenever new code is added without going through an ASCII audit

## What Didn't Work
- Relying on emoji and rich glyphs for visual polish. They disappear on CP-1252 terminals — the one place they need to work most
- Per-session local cleanups. Each session fixed its own files. The next session introduced new non-ASCII characters or touched files the previous session had skipped
- Adding `# -*- coding: utf-8 -*-` headers to Python files. File encoding is not the problem — the problem is how Windows renders the bytes after Python prints them

## Solution
**Two complementary defenses.**

### 1. Force the Windows console to UTF-8 at startup
Early in `MainProgramV5_2.py`:

```python
import sys
import subprocess

if sys.platform == "win32":
    subprocess.run(["chcp", "65001"], capture_output=True, shell=True)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
```

This sets the console code page to 65001 (UTF-8) and reconfigures Python's stdout to emit UTF-8. It fails gracefully on environments that don't support reconfiguration — judges who open the program from an unconfigured terminal still see something readable, just without the box-drawing.

### 2. ASCII-only for functional text, box-drawing only in approved banners
- **Functional text** — competitor names, results, menu items, errors: plain ASCII only. `ADVANCES`, not `→ ADVANCES 🥇`. `OK`, not `✓`. `ERROR:`, not `❌`.
- **Box-drawing** (`╔═╗║╚╝`) — allowed only in the approved 70-char banner pattern documented in [CLAUDE.md "ASCII Art Alignment"](../../../CLAUDE.md). Every banner must use `.center(68)` for centering, never manual spaces. New banners must be reviewed against the approved examples:
  - [MainProgramV5_2.py single-event menu](../../../MainProgramV5_2.py) (lines 194–205, "HANDICAP CALCULATION SYSTEM")
  - [MainProgramV5_2.py multi-event menu](../../../MainProgramV5_2.py) (lines 745–753, "TOURNAMENT CONTROL SYSTEM")
- **Arrows, emojis, checkmarks, medals** — forbidden anywhere in program output

## Why This Works
Setting the code page to UTF-8 covers the 80% case: a Windows terminal that knows what to do with multi-byte characters. The ASCII-only rule for functional text covers the 20% edge case: Windows Terminal builds, IDE-embedded terminals, remote SSH sessions, and headless CI runs where UTF-8 might not stick.

Restricting box-drawing to approved banners with a strict 70-char width means:

1. Future contributors cannot "add a quick box here" without going through the banner standard
2. The banners that exist are small in number and can be visually verified
3. When a Windows terminal degrades the banner, it degrades consistently — the user sees the same shape of failure every time, not different kinds of garbling in different menus

The recurrence pattern in git history (V5.2.1, then V5.2.1 follow-up, then Apr 2026 ruff cleanup) is the tell: **sweeps must be comprehensive, not local.** Every time a session touches UI code, it must grep the entire codebase for new non-ASCII characters, not just fix the ones in the current file.

## Prevention
- Keep the `chcp 65001` + stdout reconfigure block at the top of `MainProgramV5_2.py`. Do not remove it for "cleanliness" — it is a defensive runtime fix
- When adding new UI code, grep for non-ASCII characters before committing: a non-ASCII search over your diff should return either (a) approved banner characters in an approved banner, or (b) nothing
- New banners get added to CLAUDE.md's approved-examples list in the same commit, with line numbers. If it isn't approved, it isn't allowed
- Code review checklist should include: "any new non-ASCII character in output?" and "is it in an approved banner?"
- Run the program on a fresh, unconfigured Windows PowerShell at least once before shipping a UI change. Windows Terminal hides the bug; PowerShell reveals it
- When ruff or other formatters rearrange string literals that contain box-drawing characters, visually verify the banner still aligns. Ruff has reordered string concatenations in the past and broken alignment
- If a banner needs visual distinction that plain ASCII cannot provide, extend the approved banner list rather than introducing new glyphs ad-hoc

## Related Issues
- [CLAUDE.md "CRITICAL DEVELOPMENT RULE - ASCII ART ALIGNMENT"](../../../CLAUDE.md)
- [MainProgramV5_2.py](../../../MainProgramV5_2.py) — the `chcp 65001` + reconfigure block at file top
- Commits `18292c5`, `4cb372b` — the two V5.2.1 cleanup passes
- Commit `45accff` — ruff adoption (verify no banners were broken in that pass)
