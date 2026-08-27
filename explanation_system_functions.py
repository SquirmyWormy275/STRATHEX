# -*- coding: utf-8 -*-
"""Interactive operator help for STRATHEX prediction-engine operation."""


def _pause() -> None:
    input("\nPress Enter to return to help...")


def _overview() -> None:
    print("""
======================================================================
STRATHEX 7 RUNTIME OVERVIEW
======================================================================

STRATHEX manages competitors, wood, tournament state, results, and the judge
workflow. STRATHMARK 2.0 owns numeric predictions, calibrated uncertainty,
performance spread, and joint handicap-mark optimization.

Every field uses one exclusive evidence cutoff. Historical results on or after
that date are excluded, so a resumed event produces the same calculation from
the same evidence.
""")
    _pause()


def _prediction_contract() -> None:
    print("""
======================================================================
STRATHMARK V2 PREDICTIONS
======================================================================

The live model is one prior-only hierarchical core. Manual overrides remain
operator authority. A residual model is inactive unless STRATHMARK explicitly
promotes it. Numeric LLM prediction and the former local XGBoost/expected-error
cascade are retired.

Stable competitor IDs and dated history cross the boundary. Wood quality and
same-tournament times are retained as context but do not affect v2 numerics.
Undated, same-day, future, or otherwise invalid evidence is excluded.
""")
    _pause()


def _uncertainty_and_marks() -> None:
    print("""
======================================================================
UNCERTAINTY AND MARKS
======================================================================

The 90% forecast interval describes uncertainty in the predicted time.
Performance standard deviation describes race-to-race spread. They are not the
same value.

STRATHMARK assigns marks for the entire field with a deterministic joint
optimizer. STRATHEX displays the engine, model, calibration, evidence cutoff,
optimizer, warnings, degraded state, provenance, and ignored factors returned
by the engine.
""")
    _pause()


def _transport_and_persistence() -> None:
    print("""
======================================================================
TRANSPORT AND PERSISTENCE
======================================================================

Default transport: direct Python, suitable for offline race-day operation.
Optional demo transport: STRATHMARK FastAPI POST /calculate. Select it with
STRATHMARK_TRANSPORT=http and STRATHMARK_API_URL. HTTP mode checks the exact
2.0.0 API contract and never silently falls back to Python. Remote URLs require
HTTPS; loopback HTTP is allowed.

Excel is the judge-canonical result record. ResultStore is a best-effort derived
history store written after Excel succeeds; the two writes are not one atomic
transaction. PredictionLedger receipts are a separate STRATHMARK facility and
the public calculation route is stateless.
""")
    _pause()


def show_prediction_engine_help(*, pause: bool = True) -> None:
    """Explain the deliberate competition-scoped V2/V3 authority choice."""
    print("""
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
""")
    if pause:
        _pause()


def explanation_menu() -> None:
    """Show concise help that matches the live runtime."""
    while True:
        print("""
======================================================================
STRATHEX 7 HELP
======================================================================
1. Runtime overview
2. STRATHMARK v2 prediction contract
3. Uncertainty and mark optimization
4. Transport and persistence boundaries
5. Choosing STRATHMARK V2 or V3
0. Return to main menu
======================================================================
""")
        choice = input("Select a topic: ").strip()
        if choice == "1":
            _overview()
        elif choice == "2":
            _prediction_contract()
        elif choice == "3":
            _uncertainty_and_marks()
        elif choice == "4":
            _transport_and_persistence()
        elif choice == "5":
            show_prediction_engine_help()
        elif choice == "0":
            return
        else:
            print("Invalid choice.")
