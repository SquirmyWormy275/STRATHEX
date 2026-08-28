# -*- coding: utf-8 -*-
"""Judge-facing help and the STRATHEX prediction-engine ASCII Wizard."""

from __future__ import annotations

from collections.abc import Callable

InputFn = Callable[[str], str]


def _reader(input_fn: InputFn | None) -> InputFn:
    """Resolve input at call time so tests and embedded callers can inject it."""
    return input if input_fn is None else input_fn


def _pause(input_fn: InputFn | None = None, message: str = "Turn the page") -> None:
    _reader(input_fn)(f"\n[{message} - press Enter] ")


def _wizard_banner() -> None:
    print(
        r"""
+====================================================================+
|                         .-~~~~~~~~-.                               |
|                        /  /\  /\    \                              |
|                       /  (o)(o)     \                              |
|                      |      <>       |                             |
|                      |   .------.    |                             |
|                       \  '------'   /                              |
|                    ____'-.______.-'____                            |
|                   /       /|  |\       \                           |
|                  /_______/ |__| \_______\                          |
|                                                                    |
|                      THE STRATHEX WIZARD                           |
|              Keeper of the Handicap Grimoire                       |
+====================================================================+
"""
    )


def _chapter_handicap_geometry(input_fn: InputFn | None = None) -> None:
    print(
        r"""
+--------------------------------------------------------------------+
| SCROLL I: THE TWO CLOCKS                                           |
+--------------------------------------------------------------------+

WIZARD: "A mark is not time chopped, apprentice. It is when the axe
may begin. Smaller marks start earlier; a larger mark starts later."

Every competitor cuts the full assigned task. Two clocks describe the race:

  raw cutting time              = first legal movement to completion
  completion on starter's count = start mark + raw cutting time

Example: Mark 18 + 27 seconds raw cutting time = completion near count 45.

For a simple field with frontmark B:

  mark = B + slowest expected raw time - competitor expected raw time

The faster expected chopper therefore waits longer. If everyone performs at
their forecast, their completions align. This is an estimate of fair staggered
starts, not a promise of a dead heat.

Rebasing every mark by the same amount is a COMMON TRANSLATION. It changes the
displayed origin, not the start gaps or anyone's estimated ability. Marks from
separately rebased heats cannot be compared or copied into a later round as if
they shared an origin; rebuild the complete new field on one common basis.
"""
    )
    _pause(input_fn)


def _chapter_authority(input_fn: InputFn | None = None) -> None:
    print(
        r"""
+--------------------------------------------------------------------+
| SCROLL II: WHO HOLDS WHICH STAFF?                                  |
+--------------------------------------------------------------------+

WIZARD: "Two names, two jobs. Mix them up and the grimoire bites."

STRATHEX MANAGES THE COMPETITION: setup, competitors, wood, tournament
structure, operator workflow, persistence, results, and what the judge sees.

STRATHMARK SUPPLIES NUMERIC FORECASTS, uncertainty, and field-relative
handicap marks through a versioned engine contract.

Neither program becomes the governing official. The judge reviews the sheet,
the starter controls releases, and the applicable officials decide legal
completion, placings, protests, and official issue. A model receipt and an
official result are different records.

The selected engine is numeric authority inside its competition scope. Human
competition authority remains human.
"""
    )
    _pause(input_fn)


def _chapter_engines(input_fn: InputFn | None = None) -> None:
    print(
        r"""
+--------------------------------------------------------------------+
| SCROLL III: TWO GRIMOIRES, NOT ONE CASCADE                         |
+--------------------------------------------------------------------+

V2 - THE DETERMINISTIC PRODUCTION BASELINE

V2 is the established production engine. It uses a prior-only statistical
core, an exclusive evidence cutoff, calibrated uncertainty, and a joint mark
optimizer. The same valid evidence and configuration reproduce the same
numeric result. It is not the retired manual/ML/LLM winner-take-all cascade.

V3 - THE ADAPTIVE ENSEMBLE RELEASE CANDIDATE

V3 gives the same sealed evidence to three independent forecasting families:

  1. Formula assessor
  2. Hierarchical ML assessor
  3. Three-member LLM council

Each family submits an independent forecast distribution. Valid forecasts are
pooled rather than choosing whichever sounds most confident. Credibility
begins on the cold-start policy and becomes ACCURACY-EARNED from settled prior
matches, so demonstrated calibration changes the ensemble weights over time.
Unavailable members abstain; they are never silently replaced or relabeled.

V3 first creates a signed PRE-FIELD raw-time forecast for seeding and grouping.
That field-independent forecast CANNOT CONTAIN A MARK. A mark exists only when
the synchronized EXACT FIELD is known and all competitors are assembled and
rebased together.

In this STRATHEX release, V3 is REHEARSAL-ONLY. Rehearsal evidence is valuable,
but it is not production authority. V2 remains production-authoritative.
"""
    )
    _pause(input_fn)


def _chapter_selection_and_recovery(input_fn: InputFn | None = None) -> None:
    print(
        r"""
+--------------------------------------------------------------------+
| SCROLL IV: THE DELIBERATE CHOICE                                   |
+--------------------------------------------------------------------+

WIZARD: "A safe spell never chooses itself while the judge is blinking."

For a SINGLE EVENT, the judge deliberately selects V2 or eligible V3 during
event setup. For a tournament, the choice is made once at the TOURNAMENT ROOT;
every child event and round INHERITS it. Children cannot override the root.

There is NO DEFAULT and NO SILENT FALLBACK. If the selected engine cannot
serve, the scope blocks instead of quietly changing the calculation method.

READINESS says whether an engine and mode have proven the required identity
and gates. Selection says what this competition deliberately chose. Those are
different decisions. Rehearsal readiness never means production readiness.

The selection LOCKS at the first authoritative numeric action. Issued marks
and completed results remain immutable. If an outcome is ambiguous after a
crash or timeout, RECOVERY exposes the durable command identity: retry that
exact command or keep the scope blocked. Do not invent a second command.

Receipts, selections, locks, readiness identities, recovery attempts, reasons,
and judge actions remain in the AUDIT trail.
"""
    )
    _pause(input_fn)


def _chapter_judge_boundary(input_fn: InputFn | None = None) -> None:
    print(
        r"""
+--------------------------------------------------------------------+
| SCROLL V: THE JUDGE STILL WEARS THE HAT                            |
+--------------------------------------------------------------------+

Ordinary fields may be presented for fast batch review, while disagreements,
degraded evidence, and recovery cases are singled out. THE JUDGE REVIEWS the
forecast, warnings, provenance, uncertainty, field marks, and audit context
before official use. The software assists; it does not award the race.

Championship events are scratch racing: everyone starts together. The
CHAMPIONSHIP and BRACKET MARK 3 boundary remains unchanged regardless of
prediction-engine selection. Mark 3 in that boundary is not a V2 or V3
handicap forecast.

Heat results can become evidence at the next permitted round boundary, but
they do not rewrite an issued heat. Heats, quarterfinals, semifinals, and
finals each require their actual field to be reconstructed and rebased.

WIZARD: "There. No smoke, no mirrors, and absolutely no retroactive changing
of winners. Keep the receipts, read the warnings, and let the judge judge."

               *      THE WIZARD HAS SPOKEN      *
"""
    )
    _pause(input_fn, "Return to the index")


def _complete_tour(input_fn: InputFn | None = None) -> None:
    _chapter_handicap_geometry(input_fn)
    _chapter_authority(input_fn)
    _chapter_engines(input_fn)
    _chapter_selection_and_recovery(input_fn)
    _chapter_judge_boundary(input_fn)


def show_prediction_engine_help(*, pause: bool = True, input_fn: InputFn | None = None) -> None:
    """Explain the deliberate competition-scoped V2/V3 authority choice."""
    print(
        """
======================================================================
CHOOSING STRATHMARK V2 OR V3
======================================================================

For a single event, the judge chooses one prediction engine during event
setup. For a multi-event tournament, the judge chooses once at tournament creation.
Every child event, heat, semifinal, and final inherits that tournament
choice; there is no per-event tournament override.

Nothing is selected by default. The screen shows V3 as checking,
production-ready, rehearsal-ready, ineligible, or status-check-failed. A failed
or incomplete readiness check never implies that V3 is safe to use. Rehearsal
mode is explicitly non-production and remains labeled wherever the engine is
shown.

The selected engine supplies the authoritative predictions and handicap marks
for that scope. There is no silent fallback to the other engine. The
choice locks when authoritative numeric work begins; changing a locked choice
requires abandoning that unused scope and creating a new one, while issued
marks and results remain immutable and auditable.

V2 is the established deterministic production baseline. V3 is the adaptive
ensemble and may be used only in the mode proven by its readiness response.
Both use the same woodchopping handicap purpose and judge approval workflow.
V3 first produces a signed pre-field raw-time forecast for seeding. That
forecast cannot contain a mark. Only after exact heat membership and stand
positions exist may V3 assemble a complete field-relative mark sheet.
Ordinary green/amber fields can be batch approved; flagged fields are reviewed
one at a time. An ambiguous command displays its durable identity and requires
the judge to retry that exact command or leave the scope blocked.
Championship and bracket Mark 3 rules do not become handicap calculations and
remain unchanged regardless of the selected prediction engine.
"""
    )
    if pause:
        _pause(input_fn, "Continue")


def explanation_menu(*, input_fn: InputFn | None = None) -> None:
    """Open the full character-driven ASCII explanation Wizard."""
    read = _reader(input_fn)
    while True:
        _wizard_banner()
        print(
            """
WIZARD: "Welcome, judge. Choose a scroll, or take the full tour before
someone tries to call a start mark a cutting time again."

  1. Read the complete grimoire (guided tour)
  2. Handicap geometry, two clocks, and rebasing
  3. STRATHEX, STRATHMARK, V2, and V3
  4. Selection, readiness, locking, recovery, and audit
  5. Judge review and championship boundaries
  H. Concise V2/V3 selector help
  0. Return to the main menu
+====================================================================+
"""
        )
        choice = read("Select a scroll: ").strip().lower()
        if choice == "1":
            _complete_tour(read)
        elif choice == "2":
            _chapter_handicap_geometry(read)
        elif choice == "3":
            _chapter_authority(read)
            _chapter_engines(read)
        elif choice == "4":
            _chapter_selection_and_recovery(read)
        elif choice == "5":
            _chapter_judge_boundary(read)
        elif choice == "h":
            show_prediction_engine_help(input_fn=read)
        elif choice == "0":
            print('\nWIZARD: "Grimoire closed. The marks remain auditable."')
            return
        else:
            print('\nWIZARD: "That rune is not in the index. Choose 0-5 or H."')


if __name__ == "__main__":
    explanation_menu()
