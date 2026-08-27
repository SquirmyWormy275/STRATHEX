# Competition-Scoped Prediction Engine Authority

**Status:** accepted and implemented for evaluation

## Decision

STRATHEX requires the judge to choose V2 or V3 once for a single event or once at tournament creation. A tournament's child events and rounds inherit that root choice and cannot override it. There is no default and no error path may invoke the unselected engine.

## Why the architecture pivoted

The earlier V3 design assumed one global cutover after qualification, leaving V2 as historical audit evidence. Real-user evaluation needs a different boundary: separate competitions must be able to run either reviewed mechanism long enough to compare accuracy, review burden, reliability, and judge feedback. A global switch could not provide that controlled comparison, while per-event selection inside one tournament would mix authority and make later-round evidence incoherent.

The pivot therefore changes the unit of engine authority from the installation to the competition scope. It does not change issued results, handicap winner determination, championship Mark 3 rules, or V2's numeric behavior.

## Consequences

- STRATHEX owns the deliberate human choice, persistence, inheritance, display, and recovery workflow.
- STRATHMARK owns engine eligibility, calculations, signed receipts, and V3 lifecycle evidence.
- V3 rehearsal remains visibly non-production; this decision is not a production cutover.
- V3 seeding forecasts are field-independent and mark-free. Exact field membership is required before mark assembly.
- Outages block the selected scope. Recovery retries the same durable command; it never falls back.
- Completed scopes retain comparable evidence, but software does not automatically declare a winning engine.
