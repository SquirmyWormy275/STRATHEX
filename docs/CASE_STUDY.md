# Case Study: Migrating STRATHEX to STRATHMARK 2

## Problem

STRATHEX v6.0.1 invoked STRATHMARK through Python, but its adapter still ran the older local ML/LLM comparison, selected one value, and injected it into the engine as a manual override. Under STRATHMARK 2 this would have hidden v2 calibration and provenance and treated model output as judge authority.

A real 12-competitor field demonstrated the impact: the proper v2 field calculation changed 8 of 12 marks compared with the bridge. This made the upgrade a breaking model-governance change, not a dependency bump.

## Decision

STRATHEX 7 lets STRATHMARK own the full field calculation. The offline default is a direct Python call. An explicit HTTP demo mode sends the same stateless field request to `POST /calculate`. No silent fallback is permitted.

The exact engine source is pinned because STRATHMARK 2.0 has no tag or PyPI distribution yet.

## Implementation

- stable roster IDs cross both transports;
- one event cutoff is persisted and reused;
- v2 response metadata is stored and displayed;
- bracket and championship paths use the same boundary;
- later rounds recalculate only for changed field composition, not same-day weighting;
- the API contract and response engine version are verified;
- remote plaintext API URLs are rejected;
- ResultStore receives stable competition identity and is backed up before migration;
- old numeric LLM/XGBoost runtime dependencies are removed.

## Verification

A fixed-cutoff fixture is calculated through direct Python and FastAPI. The release gate compares names, stable IDs, marks, predicted times, engine/model/calibration versions, cutoff, optimizer, interval, provenance, and ignored factors.

Tournament replay verifies save/reload across heats and finals. Bracket tests cover byes. Persistence tests corrupt primaries and prove backup recovery. All storage used by tests is disposable.

## Lesson

An adapter can preserve function signatures while violating the downstream engine's authority model. Version compatibility therefore requires semantic parity tests and evidence/provenance review, not just successful imports.

This case study intentionally avoids mutable test totals, unverified accuracy marketing, and “production ready” claims. Release evidence belongs in dated release artifacts.
