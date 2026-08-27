# Architecture

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

V2 direct mode is offline-capable. V2 HTTP sends the complete common-wood field and history because public `/calculate` is stateless. V3 sends pseudonymous sporting data through an authenticated loopback lifecycle pinned to one reviewed contract/source identity. V3 pre-field forecasts are mark-free; exact fields and stands are required for marks.

Championship competitors are grouped when target wood and history context match. Distinct target wood or curated peak windows require separate calls. The simulator fixes one cutoff, rejects mixed model bundles, and aborts rather than producing a partial field.

Excel and ResultStore are separate writes, not a distributed transaction. V2 stateless calculation and its historical ledger remain separate. V3-selected scopes also retain durable command identities and signed lifecycle receipts.

See the repository [architecture document](https://github.com/SquirmyWormy275/STRATHEX/blob/main/docs/ARCHITECTURE.md) for the module map.
