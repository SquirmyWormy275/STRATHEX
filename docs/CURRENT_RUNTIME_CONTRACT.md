# Current Runtime Contract

**Applies to:** STRATHEX 7.0.0
**Prediction authority:** STRATHMARK 2.0.0 at commit `da5c44d07311b226c1e9842104477efaf61253fa`

## Ownership

STRATHEX owns operator interaction, tournament state, schedules, advancement, judge approval, result entry, Excel output, and local recovery.

STRATHMARK owns numeric time prediction, forecast uncertainty, race-performance spread, prediction provenance, engine health metadata, and joint handicap-mark optimization.

## Calculation

Each field has one persisted exclusive `prediction_as_of` date. STRATHEX sends stable competitor IDs, dated historical observations, target wood, and event code under that cutoff.

STRATHMARK v2 uses its prior-only hierarchical core. Manual overrides remain authoritative. The optional residual is inactive unless STRATHMARK promotes it. Numeric LLM and the former local XGBoost/expected-error cascade are retired.

Same-day and future observations are excluded. Undated observations are not v2 evidence. Wood quality, division, heat, field-strength compatibility fields, and same-tournament results do not change v2 numeric output. The UI must not claim otherwise.

The returned contract includes predicted time, legal mark, method, confidence, explanation, forecast interval, performance standard deviation, engine/model/calibration versions, evidence cutoff, optimizer and metadata, warnings, degraded state, provenance, ignored factors, competitor ID, and optional ledger fields.

## Transport

- `python` is the default: direct in-process `HandicapCalculator.calculate()`, offline-capable.
- `http` is explicit: one stateless `POST /calculate` per common-wood field after validating the audited `/openapi.json` 2.0.0 request/response shape.
- HTTP mode never falls back to Python.
- Loopback HTTP is allowed. Remote API URLs require HTTPS. Redirects and URLs containing credentials, paths, queries, or fragments are rejected. OpenAPI and calculation response bodies are bounded to 4 MiB.
- The HTTP calculation endpoint does not read ResultStore and does not write PredictionLedger.

Both transports enforce the public API's 64-competitor field-size and value bounds before calculation. A malformed or incomplete result aborts the complete field. Championship scenarios group competitors that share target wood and history context; distinct target wood or curated peak windows require separate calls. The simulator fixes the cutoff, requires one consistent engine/model/calibration bundle, and aborts rather than mixing snapshots or producing a partial field.

STRATHEX prohibits multi-event recalculation after results entry begins. Recalculating a scheduled event invalidates its generated heats. If recalculation fails, STRATHEX clears that event's prior marks and pending rounds, sets `status=recalculation_failed`, saves the failure state, and blocks results entry, schedule generation, and schedule export until a successful recalculation and fresh schedule generation. It never leaves stale v6 or earlier v7 marks available to judges.

Simulation remains local. Championship simulation uses at most 250,000 races and an adaptive two-million competitor-cell cap, and it does not retain an unused per-race finish-spread list.

## Persistence

Excel is judge-canonical. ResultStore is a derived, best-effort second write. The two stores are not one atomic transaction and a ResultStore failure does not undo Excel.

Tournament JSON saves are schema-validated, written to a same-directory temporary file, flushed, verified, atomically replaced, and backed up. Load can recover a valid backup when the primary is malformed.

A one-time `.pre-v2.bak` SQLite snapshot protects an existing ResultStore before v2 schema migration. It includes committed WAL rows, passes SQLite integrity validation, and is atomically published. New result writes include `competition_id` and the event date.

ResultStore history and PredictionLedger receipts are separate. STRATHEX does not currently use trusted ledger calculation or settlement routes.

## Release gates

A STRATHEX release is acceptable only when:

1. direct and HTTP transports match on a fixed-cutoff field;
2. stable identity and v2 metadata survive save/reload;
3. all tournament replay, bracket-bye, atomic-state, and result-write tests pass against isolated storage;
4. Ruff, wheel build, and clean-wheel import smoke pass;
5. maintained docs, dated solution labels, and versioned wiki source describe this contract;
6. published wikis are synced and verified separately;
7. no test touches the production workbook or ResultStore.
