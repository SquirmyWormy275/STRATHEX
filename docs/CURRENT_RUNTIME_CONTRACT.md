# Current runtime contract

This file is the maintained documentation authority for the STRATHEX
executable. Historical reports in `docs/archive/` and `SYSTEM_STATUS.md` retain
investigation context but must not be used to infer current behavior.

## Authority and boundaries

- `MainProgramV5_2.py` remains the compatibility launcher for existing Windows
  shortcuts. Its displayed version comes from `woodchopping.__version__`.
- `woodchopping/strathmark_adapter.py` is the application boundary for
  handicap-engine calls.
- `pyproject.toml` pins STRATHMARK at commit `47bb143`. STRATHMARK 2.0 is not a
  dependency-only upgrade; its behavioral differences are documented in
  `STRATHMARK_2_COMPATIBILITY_EVALUATION.md`.
- Excel is the judge-portable canonical result record. STRATHEX also dual-writes
  to the local STRATHMARK ResultStore. No local test authorizes a hosted,
  multi-judge, or production deployment claim.

## Operator data and workflow contract

- Wood quality is entered as an integer from 1 through 10: 1 is softest, 5 is
  neutral/average, and 10 is hardest.
- The pinned engine enforces a mark floor of 3 and a system mark ceiling of 183
  seconds. Predicted-time gaps use Python's half-to-even `round()` behavior.
- Single-event and multi-event saves use a validated temporary file, atomic
  replacement, and a rolling last-known-good `.bak`.
- Malformed nested round/event structures are rejected on load. A valid backup
  is recovered automatically and the judge is notified.
- Multi-event days support handicap and championship events. Brackets use the
  dedicated single-event workflow; legacy multi-event bracket states are
  rejected instead of being misrouted through handicap heat logic.
- Bracket events are view-only and never write race results to Excel or the
  ResultStore.

## Required release evidence

1. Tests use an isolated STRATHMARK database, temporary state directory, and
   disposable workbook.
2. The non-Ollama test suite and Ruff checks pass.
3. A complete heat-to-final replay saves, reloads, resumes, and dual-writes only
   to isolated stores.
4. A non-power-of-two bracket resumes through byes to a champion without result
   writes.
5. The wheel is imported from outside the repository checkout.
6. `python scripts/terminal_gallery.py` is captured and inspected in the target
   Windows terminal.

Green automated tests are evidence for these contracts, not a general claim of
field or production readiness.
