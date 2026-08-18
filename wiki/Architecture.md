# Architecture

```text
Judge -> STRATHEX terminal
          |-- tournament state and UI
          |-- Excel canonical results
          |-- atomic JSON saves
          |-- best-effort ResultStore
          |
          +-- direct Python (default) --+
          +-- HTTP /calculate (demo) ---+--> STRATHMARK 2
                                             prior-only prediction
                                             calibrated uncertainty
                                             joint mark optimizer
```

STRATHEX owns workflow and persistence decisions. STRATHMARK owns numeric prediction and mark optimization. The adapter is the only live calculation boundary.

Direct mode is offline-capable. HTTP mode sends the complete common-wood field and history because public `/calculate` is stateless. It validates the audited OpenAPI 2.0.0 `/calculate` shape and returned audit metadata, refuses redirects, and has no silent fallback. Both transports apply the same field limits before calculation.

Championship competitors are grouped when target wood and history context match. Distinct target wood or curated peak windows require separate calls. The simulator fixes one cutoff, rejects mixed model bundles, and aborts rather than producing a partial field.

Excel and ResultStore are separate writes, not a distributed transaction. ResultStore history, PredictionLedger receipts, and stateless API calculation are separate concepts.

See the repository [architecture document](https://github.com/SquirmyWormy275/STRATHEX/blob/main/docs/ARCHITECTURE.md) for the module map.
