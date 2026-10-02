# Changelog

## 7.1.0

- Added deliberate competition-scoped V2/V3 selection, tournament inheritance, authenticated V7 pre-field forecasts and exact-field marks, durable command recovery, issue/settlement acknowledgments, and the ASCII explanation Wizard previously merged after v7.0.0.
- Preserved V2 production authority and V3 rehearsal-only behavior, with no engine fallback.
- Repaired the fresh-tournament finance menu, unset bracket competitors, roster identity reuse, nonpositive menu selections, payout restoration after save/resume, invalid manual-history dates, out-of-range wood quality, championship personal-best column names, and tournament menu numbering.
- New competitor IDs are opaque UUID-backed identities. Existing IDs are preserved; duplicate existing IDs block roster additions.
- Updated the reviewed API test set to FastAPI 0.142.2, Starlette 1.7.0 and HTTPX2 2.13.1, with parity and contract verification.
- Added a portable `strathex` launcher with explicit workbook and operator-data paths and an installed-app smoke on Linux and Windows.
- Reconciled current documentation and wiki source, added contributor guidance, pinned lint/actions, added dependency-update proposals and enforced merge checks.

## 7.0.0 — 2026-08-18

Migrated numeric workflows to the pinned STRATHMARK V2 field contract, with direct/HTTP parity, stable IDs, prior-only cutoffs, calibrated intervals, joint mark optimization, and recoverable persistence. See [the original release notes](docs/RELEASE_v7.0.0.md).

## 6.0.1 — 2026-08-18

Repaired the earlier integration bridge, workbook recovery, tournament replay, JSON saves, bracket byes, and terminal rendering. See [the original release notes](docs/RELEASE_v6.0.1.md).
