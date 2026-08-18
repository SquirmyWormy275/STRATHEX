# -*- coding: utf-8 -*-
"""Interactive operator help for the live STRATHEX 7 / STRATHMARK v2 runtime."""


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
        elif choice == "0":
            return
        else:
            print("Invalid choice.")
