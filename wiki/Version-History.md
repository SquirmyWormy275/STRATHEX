# Version History

Release highlights. See [`docs/SYSTEM_STATUS.md`](https://github.com/SquirmyWormy275/STRATHEX/blob/main/docs/SYSTEM_STATUS.md) for a full per-feature status table.

---

## V6.0 (Mar 2026)

**STRATHMARK engine extraction.** The biggest architectural change since V4.0.

- All handicap math, Monte Carlo simulation, prediction aggregation, and AI fairness assessment moved into [STRATHMARK](https://github.com/SquirmyWormy275/STRATHMARK) — a separate, pip-installable package.
- STRATHEX becomes the tournament-management surface only. Calculations are delegated through [`woodchopping/strathmark_adapter.py`](https://github.com/SquirmyWormy275/STRATHEX/blob/main/woodchopping/strathmark_adapter.py).
- **SQLite persistence** — results now live in `~/.strathmark/results.db` and accumulate across competitions. Dual-write (Excel + SQLite) on every save. Startup migration is idempotent.
- **Expected-error selection** — `select_best_prediction()` replaces the old fixed-priority cascade. A HIGH-confidence LLM prediction now correctly beats a LOW-confidence baseline.
- **HTTP REST API** — STRATHMARK ships a FastAPI layer for non-Python consumers. STRATHEX continues to use the Python import API (zero overhead).
- **Mark rounding changed** — V5.2 used `ceil()` (round up). V6.0 uses Python `round()` (banker's rounding, half-to-even). Avoids systematic upward bias.

Branches:
- `main` = V6.0
- `v5.2-legacy` = V5.2 (pure local calc, no STRATHMARK dependency)

---

## V5.2 (Jan 2026)

- **Tournament payout configuration** — per-event prize money, aggregated earnings leaderboard
- **Position-based draw logic** — fair advancement draws across rounds
- **Ollama connection caching** — prevents the error-spam loop when LLM is unavailable
- **Multi-event round generation fix** — heats-to-finals path in multi-event mode
- **DataFrame JSON serialization** — tournament state saves now survive DataFrame roundtripping

---

## V5.1 (Jan 2026)

**Wood mechanics + sparse-data rigor.**

- **Comprehensive wood properties** — expanded ML features from 19 to 23, adding shear strength, crush strength, MOR, and MOE. Combined correlation r=0.621 (18.7% improvement over shear alone). Baseline updated to weight all 6 mechanical properties.
- **Sparse-data validation** — three-tier (BLOCKED / WARNING / SUFFICIENT) gating. N<3 blocks competitor selection; N=3–9 shows inline warning and downgrades confidence to LOW.
- **High-variance diameter flagging** — CoV warnings for 279mm, 254mm, 270mm, 275mm diameters. Recommends standard sizes (300mm, 250mm, 225mm) when CoV exceeds 60%.
- **Event code normalization** — fixes the UH/uh, SB/sb case-sensitivity bug. All codes forced uppercase at load/save/append. Historical data unified (393 `uh` + 139 `UH` → unified `UH`).

---

## V5.0 (Jan 2026)

**Championship Simulator and Brackets.**

- **Championship Race Simulator** (Main Menu Option 3) — 2M Monte Carlo iterations, AI race commentary, view-only analysis tool
- **Bracket Tournaments** — single and double elimination with AI-powered seeding, ASCII tree + HTML export
- **Multi-Event Tournaments** (expanded) — tournament-day workflow with per-event wood/competitor/format configuration
- **Prize money / payout system** — per-event configuration, earnings leaderboard
- **Monte Carlo individual statistics** — per-competitor mean, std_dev, percentiles, consistency ratings
- **Schedule printout generator** — human-readable heat schedules
- **Live results entry with standings** — real-time leaderboard during results entry
- **Handicap Override Tracker** — audit log of every manual adjustment
- **Competitor Performance Dashboard** — per-competitor history view
- **Prediction Accuracy Tracker** — tracks predicted-vs-actual across events

---

## V4.5 (Jan 2026)

- **Multi-event tournament management** — complete tournament-day workflow (first implementation; expanded in V5.0)

---

## V4.4 (Dec 2025)

- **QAA empirical diameter scaling** — replaced power-law formula with QAA lookup tables. 150+ years of Australian competition data, separate tables for Hardwood/Medium/Softwood, triangular-membership interpolation based on effective Janka hardness.
- **Tournament result weighting** — automatic 97%/3% blending of heat results into semi/final predictions. Same wood across rounds = most accurate predictor available.

---

## V4.3 (Dec 2025)

- **Time-decay consistency** — all prediction methods now use the same exponential decay (2-year half-life). Fixes aging-competitor over-prediction.
- **Wood quality integration** — ±2% per quality point adjustment, applied to all methods (previously LLM-only).

---

## V4.0 (Dec 2025)

**Modular architecture rewrite.**

- Separate SB and UH ML models
- Modular package structure (`woodchopping/data/`, `woodchopping/predictions/`, etc.)
- Cascading fallback logic for predictions
- XGBoost with 6-feature feature engineering (expanded to 23 in V5.1)

---

## Earlier versions

V1–V3 were the monolithic prototypes — pre-modular, single-event only, no ML. Preserved in git history for provenance but no longer supported.

---

## Branch map

| Branch | Purpose |
|---|---|
| `main` | V6.0 — current production |
| `v5.2-legacy` | V5.2 — pure local calc, no STRATHMARK dep. Maintained for offline/airgapped environments |

The `v5.2-legacy` branch gets critical bug fixes only. New features land on `main` against the STRATHMARK-backed architecture.

---

## Migration notes

### V5.2 → V6.0

- **Automatic.** The STRATHMARK dependency pulls in on next `pip install -e .`. Your `woodchopping.xlsx` is unchanged. On first startup, STRATHEX migrates the `Results` sheet into `~/.strathmark/results.db` (idempotent; safe to re-run).
- **Rounding changed.** Marks computed on V5.2 Excel saves may differ from V6.0 re-computations by ±1 second on exact half-seconds. Not a bug — see above.
- **Tournament state files from V5.2 may not load.** Severity depends on use case. Open an issue if blocked.

### V4.x → V5.x

- Schema additions to the `wood` sheet (shear, crush, MOR, MOE columns). Rows missing these get a reduced feature set — not fatal, just slightly less accurate ML.
- Event code normalization — any case-mixed data is automatically cleaned on first V5.1 startup.

---

## Further reading

- [`docs/SYSTEM_STATUS.md`](https://github.com/SquirmyWormy275/STRATHEX/blob/main/docs/SYSTEM_STATUS.md) — full per-feature current status
- [STRATHMARK CHANGELOG](https://github.com/SquirmyWormy275/STRATHMARK/blob/main/CHANGELOG.md) — engine release notes
- [Architecture](Architecture) — current V6.0 layout
- [Ecosystem](Ecosystem) — cross-repo relationship
