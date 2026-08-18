# STRATHMARK 2 Migration Decision

**Status:** superseded as a compatibility warning and completed by STRATHEX 7.0.0.

The v6.0.1 evaluation correctly found that simply changing the dependency pin was unsafe. STRATHMARK 2 deliberately changed prediction authority, evidence rules, uncertainty, and mark optimization. Feeding the old expected-error winner through `manual_overrides` would have mislabeled model output as judge authority and bypassed v2 calibration.

STRATHEX 7 accepts those semantic changes and replaces the bridge.

## Accepted v2 contract

- prior-only hierarchical core;
- exclusive fixed cutoff and stable identity;
- undated/same-day/future evidence excluded;
- numeric LLM retired;
- legacy ML input ignored unless a promoted residual exists;
- wood quality and tournament context numeric no-ops;
- calibrated forecast interval distinct from performance standard deviation;
- deterministic joint optimizer;
- complete warnings, degraded state, provenance, and ignored-factor metadata.

## Migration implementation

- Exact engine pin: `da5c44d07311b226c1e9842104477efaf61253fa`.
- Direct Python is the offline default.
- Explicit HTTP mode uses one stateless `POST /calculate` per field.
- HTTP checks OpenAPI 2.0.0 and returned engine metadata; no silent fallback.
- Bracket and championship prediction paths now use the same adapter.
- Event cutoff and v2 metadata persist in tournament state.
- Existing ResultStore receives a one-time pre-v2 backup before schema migration.
- New result writes include stable competition identity.
- Maintained docs and wiki source no longer present the v6 predictor cascade as current.

## Verification requirement

A fixed-cutoff field must produce the same marks, predictions, versions, intervals, optimizer, provenance, and ignored factors through direct Python and HTTP. That parity test is a permanent release gate.

The original v6.0.1 decision remains available in Git history and the dated v6.0.1 release/audit documents. Those documents describe that release, not the current runtime.
