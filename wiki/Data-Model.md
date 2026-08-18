# Data Model

## Competitor identity

Roster rows carry stable competitor IDs and display names. STRATHEX passes both to STRATHMARK. Name remains judge-facing; ID anchors prediction population state and future trusted persistence.

## Historical result

A result includes competitor identity, event code, raw time, species, diameter, quality, heat ID, result date, and stable competition ID. V2 evidence requires a valid date before the field cutoff.

## Tournament state

Single and multi-event state includes:

- competitors and DataFrame records;
- wood and event configuration;
- format, rounds, status, advancement, and placements;
- handicap results including v2 metadata;
- one persisted `prediction_as_of`;
- optional payout and adjustment records.

## Persistence systems

- Excel: judge-canonical results.
- JSON save: recoverable workflow state.
- ResultStore: best-effort local historical evidence.
- PredictionLedger: immutable STRATHMARK prediction receipts and settlements; not used by public STRATHEX calculation.
- `POST /calculate`: stateless; it reads only the request.

Do not describe these stores as automatically synchronized or cross-store atomic.
