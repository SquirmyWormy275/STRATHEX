# Ecosystem

## STRATHEX

Judge-facing tournament operations: roster, event configuration, schedules, marks display, approval, results, advancement, payouts, saves, and exports.

## STRATHMARK

Prediction and settlement authority: v2 predictive distribution, calibration, performance spread, mark optimization, provenance, health metadata, ResultStore history, and optional PredictionLedger receipts.

STRATHEX 7 consumes STRATHMARK through direct Python or explicit stateless HTTP calculation. It does not use trusted ledger calculation yet.

## MNEMEX

Portable competitor identity and finalized history. MNEMEX must not become a race-day network dependency. Event laptops use pinned local snapshots and reconcile after the event.

## Missoula Pro-Am Manager

Owns its live/provisional event results and operator workflow. Optional STRATHMARK shadow integration remains a separate trusted contract and is not the same as STRATHEX's public stateless demo route.

## Authority boundary

Live/provisional results belong to the event application. Portable finalized history belongs to MNEMEX. Prediction and settlement receipts belong to STRATHMARK. No service should silently assume another system's authority.
