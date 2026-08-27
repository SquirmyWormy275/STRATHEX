# System Status

**Current target:** competition-scoped STRATHMARK V2/V3 selection in STRATHEX
**Status date:** 2026-08-27

## Implemented

- Direct-Python STRATHMARK v2 calculation as the offline default.
- Explicit FastAPI `POST /calculate` demo transport.
- Exact API and result engine-version checks with no silent fallback.
- Stable competitor identity and fixed exclusive evidence cutoffs.
- Full v2 interval, provenance, optimizer, warning, and degraded metadata.
- V2 bracket seeding and championship prediction.
- Atomic tournament-state persistence with structural validation and backup recovery.
- Canonical Excel result writes plus clearly documented best-effort ResultStore writes.
- Pre-v2 ResultStore backup and stable competition IDs.
- Single/multi-event replay and bracket-bye regression coverage.
- Maintained docs, in-app help, and versioned wiki source aligned to v2.
- Deliberate no-default engine selection at single-event or tournament root.
- Tournament-wide inheritance with no child-event override and no engine fallback.
- Readiness-gated V3 rehearsal using authenticated loopback lifecycle calls.
- Mark-free V3 pre-field seeding forecasts followed by exact-field mark assembly.
- Durable V3 recovery identities and exception-first approval review.

## Explicit boundaries

- Excel and ResultStore are not transactionally atomic together.
- Public HTTP calculation is stateless and unauthenticated.
- V2 PredictionLedger trusted routes remain separate; V3-selected scopes use signed V3 lifecycle receipts.
- Remote HTTP requires HTTPS; loopback HTTP is for the demo.
- Simulation remains local and is not transport-parity with the capped REST simulation endpoint.
- Undated and same-day results are excluded by the v2 prior-only contract.
- Wood quality and same-tournament times do not change v2 numerics.
- Legacy local XGBoost/LLM modules are compatibility/history code, not live prediction authority.
- V3 production mode remains unavailable without installation-owned evidence; this work does not cut over the installation globally.

## Remaining release operations

- full isolated suite, Ruff, build, and clean-wheel smoke;
- copied ResultStore migration rehearsal;
- operator terminal gallery and Windows smoke;
- independent diff review;
- feature-branch PRs and hosted checks;
- publish and verify STRATHEX and STRATHMARK GitHub wikis;
- create coordinated tags/releases only after those gates pass.

This page does not claim deployment, public API security, or production readiness before those operations complete.
