# Data Model

STRATHEX reads and writes two data stores:

1. **Excel** — `woodchopping.xlsx` at the project root. Human-readable, editable, canonical for judges.
2. **SQLite** — `~/.strathmark/results.db`. Cross-competition history; engine's learning substrate.

Every results save is dual-write and atomic. On startup, STRATHEX runs an idempotent migration from Excel into SQLite (`INSERT OR IGNORE`). Both stores can be backed up independently.

---

## Excel schema

`woodchopping.xlsx` must contain three sheets:

### 1. `Competitor`

Master roster. One row per competitor.

| Column | Type | Required | Description |
|---|---|---|---|
| `CompetitorID` | int | yes | Stable unique ID. Used internally for joins |
| `Name` | str | yes | Display name |
| `Country` | str | optional | Country code or full name |
| `State/Province` | str | optional | State, province, or territory |
| `Gender` | str | optional | M / F / Other |

STRATHEX uses both ID-based and name-based lookup. ID is canonical; name is a display/UX convenience. See `get_competitor_id_name_mapping()` for the bidirectional mapping.

### 2. `wood`

Species catalog. One row per wood species the system knows about.

| Column | Type | Required | Description |
|---|---|---|---|
| `Species` | str | yes | Common name (e.g., "Cottonwood", "Eastern White Pine") |
| `Janka Hardness` | float | yes | lbf (pounds-force to embed a steel ball half its diameter) |
| `Specific Gravity` | float | yes | Relative density vs. water |
| `Shear Strength` | float | optional | Parallel-to-grain shear (psi) |
| `Crush Strength` | float | optional | Parallel-to-grain compression (psi) |
| `MOR` | float | optional | Modulus of rupture (bending strength, psi) |
| `MOE` | float | optional | Modulus of elasticity (stiffness, psi × 10⁶) |
| `Difficulty Multiplier` | float | optional | Legacy; not used in V6.0 |

All 6 mechanical properties feed the ML model (V5.1 expansion — see [Version History](Version-History)). Species without all 6 properties fall back to a reduced feature set.

Adding a new species:
1. Add a row to the `wood` sheet
2. Restart STRATHEX (reloads on next tournament run)
3. The species appears in the wood-selection dropdown

### 3. `Results`

Historical result database. One row per individual competitor performance.

| Column | Type | Required | Description |
|---|---|---|---|
| `CompetitorID` | int | yes | Foreign key to `Competitor.CompetitorID` |
| `Event` | str | yes | `SB` or `UH` (normalized to uppercase; see below) |
| `Time` | float | yes | Raw cut time in seconds |
| `Species` | str | yes | Must exist in the `wood` sheet |
| `Size` or `Diameter` | int | yes | Block diameter in mm |
| `Quality` | int | optional | 0–10 rating (defaults to 5 if missing) |
| `HeatID` | str | yes | Tournament grouping — see below |
| `Date` | date | optional | ISO date. Used by time-decay |

#### HeatID format

```
<EVENT_CODE>-<EVENT_NAME>-<ROUND_NAME>

Examples:
  SB-225MM-HEAT1
  UH-300MM-SEMIFA
  SB-275MM-NOV-FINAL
  UH-CHAMP-300MM-FINAL      ← Championship event
```

Event-aware HeatIDs let you pull all rounds of a specific event without pulling unrelated events from the same tournament day.

#### Event code normalization

V5.1 fixed a critical bug where mixed-case codes (`UH` vs. `uh`) were treated as different events. All codes are now normalized to uppercase at load/save/append. Historical data was unified (legacy `uh` records merged into `UH`). See [Version History § V5.1](Version-History#v51-jan-2026).

---

## SQLite schema (ResultStore)

Location: `~/.strathmark/results.db` (platform-dependent — `%USERPROFILE%\.strathmark\results.db` on Windows).

### `results` table

```sql
CREATE TABLE results (
    id                INTEGER PRIMARY KEY,
    competitor_name   TEXT NOT NULL,
    competitor_id     INTEGER,
    event             TEXT NOT NULL,       -- 'SB' or 'UH'
    raw_time          REAL NOT NULL,
    species           TEXT,
    diameter_mm       INTEGER,
    quality           INTEGER,
    heat_id           TEXT,
    event_date        TEXT,                 -- ISO date
    tournament_name   TEXT,
    source            TEXT,                 -- 'excel_migration' | 'strathex_write' | 'direct_api'
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (competitor_name, event, raw_time, species, diameter_mm, heat_id, event_date)
);

CREATE INDEX idx_results_competitor ON results (competitor_name, event);
CREATE INDEX idx_results_date       ON results (event_date);
```

The `UNIQUE` constraint is what makes startup migration idempotent — re-running `INSERT OR IGNORE` from Excel never creates duplicates.

### Why both stores?

- **Excel** is the judge's file. Portable (USB stick from one venue laptop to another), editable (open in Excel, hand-fix a typo), auditable (you can see every record), familiar to non-technical users. Canonical for anything humans interact with.
- **SQLite** is the engine's substrate. Persists across competitions, months, years. Predictions grow more accurate as more data accumulates. Indexed for fast queries. Canonical for anything the engine reads.

Both stores are kept in sync automatically. Excel is canonical for *writes* (judges edit the sheet); SQLite mirrors it. The engine reads from *both* — Excel for the current tournament's competitors, SQLite for cross-competition history.

---

## Data validation

On load, STRATHEX runs:

1. **Schema check** — all required columns present
2. **Event code normalization** — `uh` → `UH`, `sb` → `SB`
3. **Outlier detection** — 3×IQR on raw times per competitor+event (removes data-entry errors; keeps genuine exceptional performances)
4. **Species lookup** — any species referenced in `Results` must exist in `wood`
5. **CompetitorID join** — every `Results.CompetitorID` must exist in `Competitor`

Validation errors are surfaced with context — STRATHEX tells you which row, which field, and what's wrong.

---

## Tournament state files

Separately from the result database, STRATHEX saves tournament state as JSON for `/Load Previous Event`:

- **Single event:** `tournament_state_<timestamp>.json`
- **Multi-event:** `multi_event_tournament_<timestamp>.json`

These files capture:
- Wood configuration
- Competitor selection
- Computed marks (before and after manual overrides)
- Completed and pending rounds
- Results entered so far
- Payout configuration

Resume-capable — you can close mid-tournament and pick up exactly where you left off. See [Tournament Workflow § State Model](Tournament-Workflow#state-model).

---

## Data entry best practices

### For new competitors

Minimum required before they can be handicapped:
- 3 historical results on the event (SB or UH) they're entering
- Each with wood species, diameter, quality, and ideally date

Fewer than 3 → blocked (N<3 absolute minimum). 3–9 → warning (LOW confidence). 10+ → normal.

### For new species

Adding a species requires Janka hardness and specific gravity at minimum. The other 4 mechanical properties (shear, crush, MOR, MOE) are optional but recommended — they feed the ML model and improve prediction accuracy.

### For backfilling history

Older results typically have quality=5 by default (unless noted). This is an unavoidable limitation — the quality rating is a judge's in-the-moment call; you can't reconstruct it from the scorebook. The time-decay weighting mitigates this by down-weighting older records.

Date fields are important. Records without dates get a reduced weight in time-decay (treated as "unknown age"). Add dates whenever possible, even approximate.

---

## Backups

```bash
# Quick backup of everything
cp woodchopping.xlsx woodchopping.xlsx.backup
cp ~/.strathmark/results.db ~/.strathmark/results.db.backup
```

Recommended before:
- Running startup migration for the first time
- Large bulk imports from legacy sources
- Version upgrades (V5.2 → V6.0)

---

## Legacy migration

If you're coming from an older spreadsheet format, see [`STRATHMARK/import_legacy.py`](https://github.com/SquirmyWormy275/STRATHMARK/blob/main/import_legacy.py) for the bulk-import script. Handles:
- Event code normalization
- Species name aliases
- Missing columns (with sensible defaults)
- Duplicate detection

Usage:
```bash
python -m strathmark.import_legacy --input old_results.xlsx --output woodchopping.xlsx
```

---

## Further reading

- [Architecture](Architecture) — how data flows through the pipeline
- [Handicap System Explained § Stage 1](Handicap-System-Explained#stage-1--gather-history) — how history is consumed
- [STRATHMARK store.py](https://github.com/SquirmyWormy275/STRATHMARK/blob/main/strathmark/store.py) — ResultStore implementation
