# Architecture

## Available runtime profiles

STRATHEX 7.2.0 preserves V2 production operation and offers two explicitly configured V3 rehearsal profiles. The [Linux numeric candidate](https://github.com/SquirmyWormy275/STRATHEX/blob/main/docs/V3_REHEARSAL.md) runs real Formula, trained ML, pooling, and exact-field optimization through a separate Python 3.13 subprocess. Its mark-free seeding forecasts and proposed marks are unissued previews. Saved selection binds the implementation, Formula manifest, model bundle, and frozen workbook; field previews also bind revision and stand order. It cannot approve, issue, record official results, export official schedules, settle, or learn at the next round.

The authenticated V7 profile uses signed lifecycle receipts and requires full backend composition and installation qualification. Its lifecycle behavior described below applies only when that full runtime is configured and ready. The checked-in transport rehearsal uses fixtures and does not prove a real numeric lifecycle. A judge deliberately selects V2 or an available V3 profile once per competition root; failures stop the selected workflow.

```text
Judge -> STRATHEX terminal
          |-- tournament state and UI
          |-- canonical competition engine authority
          |-- Excel canonical results
          |-- atomic JSON saves
          |-- best-effort ResultStore
          |
          +-- V2 direct Python / HTTP calculate --+
          +-- V3 authenticated lifecycle API -----+--> STRATHMARK
                                                       V2 baseline or V3 ensemble
                                                       signed forecast evidence
                                                       complete-field marks
```

STRATHEX owns the deliberate competition-root choice, inheritance, workflow, names, and persistence decisions. STRATHMARK owns eligibility, numeric prediction, mark optimization, and signed evidence. An engine-neutral router binds every numeric call to the canonical selection and forbids fallback.

V2 direct mode is offline-capable. V2 HTTP sends the complete common-wood field and history because public `/calculate` is stateless. The V7 profile sends pseudonymous sporting data through an authenticated loopback lifecycle pinned to one reviewed contract/source identity. V3 pre-field forecasts are mark-free; exact fields and stands are required for marks.

Championship competitors are grouped when target wood and history context match. Distinct target wood or curated peak windows require separate calls. The simulator fixes one cutoff, rejects mixed model bundles, and aborts rather than producing a partial field.

Excel and ResultStore are separate writes, not a distributed transaction. V2 stateless calculation and its historical ledger remain separate. Full V7 scopes also retain durable command identities and signed lifecycle receipts.

See the repository [architecture document](https://github.com/SquirmyWormy275/STRATHEX/blob/main/docs/ARCHITECTURE.md) for the module map.
