# STRATHEX 7.0.0

STRATHEX 7 is the breaking migration from the legacy STRATHMARK 0.4.1 bridge to the real STRATHMARK 2.0 field-calculation contract.

## Changed

- Pins STRATHMARK commit `da5c44d07311b226c1e9842104477efaf61253fa`.
- Gives STRATHMARK v2 direct ownership of prediction, uncertainty, and joint mark optimization.
- Adds an explicit FastAPI demo transport alongside the default offline direct-Python transport.
- Fails closed on API schema/version mismatch, missing v2 audit metadata, malformed/oversized response, redirects, credential/path-bearing URLs, remote plaintext, or request failure.
- Enforces the HTTP field-size and value contract in both transports.
- Preserves stable competitor IDs and one exclusive evidence cutoff per event.
- Surfaces intervals, engine/model/calibration versions, optimizer evidence, warnings, degraded state, provenance, and ignored factors.
- Routes bracket seeding and championship prediction through the v2 adapter.
- Aborts failed advancing/championship fields instead of simulating or saving a partial competitor set.
- Caps v2-backed brackets at 64 competitors, groups common-wood championship fields, and bounds championship Monte Carlo memory.
- Removes live numeric XGBoost/LLM/expected-error behavior and the 97/3 same-tournament claim.
- Removes scikit-learn and XGBoost from runtime dependencies.
- Adds stable competition IDs to ResultStore writes and an atomic, WAL-aware, integrity-checked pre-v2 database snapshot.
- Reconciles maintained documentation, in-app help, and versioned wiki source.

## Semantic change

This release can produce different handicap marks from v6.0.1. That is intentional: v2 uses prior-only evidence and a field-level optimizer instead of the old per-competitor selection bridge. Judges must review the returned interval, provenance, warnings, degraded state, and optimizer metadata.

The compatibility result projection is also intentionally breaking: `predictions` now contains one authoritative `v2` entry instead of the former baseline/ML/LLM slots. External tools must consume the top-level v2 metadata or `predictions["v2"]`; STRATHEX does not fabricate legacy method columns.

## Upgrade

1. Back up the workbook, saves directory, and ResultStore.
2. Install the pinned dependencies.
3. Start once in direct-Python mode. STRATHEX creates `results.db.pre-v2.bak` before STRATHMARK migrates an existing store.
4. Rehearse one copied tournament and verify that 20 undated historical rows are excluded as expected.
5. For HTTP demo mode, bind STRATHMARK to loopback, set an explicit database path, and configure `STRATHMARK_TRANSPORT=http` plus `STRATHMARK_API_URL`.
6. Do not expose the public stateless calculation endpoint to an untrusted network.

## Persistence boundary

Excel remains judge-canonical. ResultStore is a best-effort second write and is not transactionally atomic with Excel. JSON tournament saves remain atomic within their own file boundary and recover from a valid rolling backup.

## Release gates

- fixed-cutoff direct/HTTP parity;
- isolated tournament replay and bracket-bye completion;
- atomic state validation and recovery;
- ResultStore migration rehearsal against a copy;
- full tests and Ruff;
- clean wheel install/import outside the checkout;
- maintained docs and versioned wiki checks;
- separate publication and verification of both GitHub wikis.
