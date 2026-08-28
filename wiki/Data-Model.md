# Data Model

## Competitor identity

Roster rows carry stable competitor IDs and display names. Name remains local and judge-facing. V3 receives only namespaced pseudonymous identifiers and calculation-required sporting facts.

## Historical result

A result includes competitor identity, event code, raw time, species, diameter, quality, heat ID, result date, and stable competition ID. V2 evidence requires a valid date before the field cutoff.

## Tournament state

Single and multi-event state includes:

- competitors and DataFrame records;
- wood and event configuration;
- format, rounds, status, advancement, and placements;
- handicap results including v2 metadata;
- one persisted `prediction_as_of`;
- an immutable reference to the canonical SQLite engine-selection authority;
- optional payout and adjustment records.

## Persistence systems

- Excel: judge-canonical results.
- JSON save: recoverable workflow state.
- ResultStore: best-effort local historical evidence.
- V2 PredictionLedger: separate from public V2 calculation.
- V3 command ledger: durable pending, acknowledged, or recovery-required command identity.
- V3 receipts: immutable forecast, field, review, issue, and settlement evidence for V3-selected scopes.
- `POST /calculate`: stateless V2 route; it reads only the request.

Do not describe these stores as automatically synchronized or cross-store atomic.
