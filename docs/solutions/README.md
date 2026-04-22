# STRATHEX Documented Solutions

This directory is the searchable knowledge store for past STRATHEX problems — bugs, architectural decisions, development practices, and workflow patterns. Each document has YAML frontmatter (`module`, `tags`, `problem_type`, `severity`) so agents can search by field.

**Relevant when:** implementing features, debugging issues, or making decisions in a documented area. Written by [`/ce:compound`](https://docs.claude.com/) after problems are solved and verified.

---

## How to use this directory

- **Grep by keyword** — most docs include concrete error messages, file paths, and commit hashes
- **Scan by category** — subdirectories group docs by problem type (see below)
- **Filter by frontmatter** — every doc has a `tags` array and a `severity` field
- **Read the "Why This Matters" or "Why This Works" section first** — those capture rationale that isn't obvious from the code

Before implementing anything that touches an area listed below, read the relevant doc first. The rationale usually matters more than the fix.

---

## Categories

### architecture-decisions/
High-level design choices and the reasoning behind them. Read these before adding or refactoring features in the affected area.

| Doc | What it covers |
| --- | --- |
| [strathmark-extraction-v6.md](architecture-decisions/strathmark-extraction-v6.md) | Why calculation was extracted into STRATHMARK in V6.0; two-buyer rationale; adapter pattern discipline |
| [qaa-scaling-removal.md](architecture-decisions/qaa-scaling-removal.md) | Why QAA tables were purged from the time-prediction path; direction-inversion bug; power-law replacement |

### best-practices/
Development disciplines and patterns that future work should follow. Each ties back to a concrete failure mode.

| Doc | What it covers |
| --- | --- |
| [prompt-feature-parity.md](best-practices/prompt-feature-parity.md) | Every system-feature change must ship with corresponding LLM prompt updates in the same commit |
| [judge-ui-simplicity-principle.md](best-practices/judge-ui-simplicity-principle.md) | Judge UI minimizes workflow change under time pressure; concrete rollbacks from V5.1 |

### build-errors/
Packaging, dependency, and build-system failures.

| Doc | What it covers |
| --- | --- |
| [hatch-allow-direct-references-2026-04-06.md](build-errors/hatch-allow-direct-references-2026-04-06.md) | Hatchling rejects `git+https://` direct references unless explicitly opted in |

### data-integrity/
Data-model correctness, Excel schema, and data-flow issues.

| Doc | What it covers |
| --- | --- |
| [wood-quality-scale-inversion.md](data-integrity/wood-quality-scale-inversion.md) | Wood quality is 1=softest / 10=hardest; historical data all recorded as 5; sign-inversion lesson |
| [sparse-competitor-data-fallback.md](data-integrity/sparse-competitor-data-fallback.md) | Competitors with no event history must be filtered out; Norah Steed incident |
| [excel-results-schema-column-mismatch.md](data-integrity/excel-results-schema-column-mismatch.md) | Results sheet 8-column schema; openpyxl atomic append; don't use `pandas.to_excel` |

### runtime-errors/
Crashes and runtime failures, typically environment- or data-dependent.

| Doc | What it covers |
| --- | --- |
| [unicode-ascii-windows-terminal.md](runtime-errors/unicode-ascii-windows-terminal.md) | Windows CP-1252 mojibake; ASCII-only functional text; approved 70-char banner standard |
| [numpy-polyfit-dlascls-sparse-data.md](runtime-errors/numpy-polyfit-dlascls-sparse-data.md) | `np.polyfit` crashes on non-finite / sparse data; defensive guard pattern |

### test-failures/
CI and pytest issues.

| Doc | What it covers |
| --- | --- |
| [pytest-collection-ollama-markers-2026-04-06.md](test-failures/pytest-collection-ollama-markers-2026-04-06.md) | `tests/conftest.py` collection rules; `ollama` marker for CI skip |
| [ml-feature-count-mismatch.md](test-failures/ml-feature-count-mismatch.md) | XGBoost trained on 19 features, inference built 7; silent `None` fall-through |

### workflow-issues/
Development-workflow gaps and their fixes.

| Doc | What it covers |
| --- | --- |
| [versioned-wiki-source-2026-04-21.md](workflow-issues/versioned-wiki-source-2026-04-21.md) | GitHub wiki versioned in `wiki/`, published via `wiki/publish.sh` |

---

## Reading order for new contributors

If you are new to STRATHEX and want the shortest path to operational understanding, read in this order:

1. **[strathmark-extraction-v6.md](architecture-decisions/strathmark-extraction-v6.md)** — understand the two-repo architecture first; everything else assumes it
2. **[qaa-scaling-removal.md](architecture-decisions/qaa-scaling-removal.md)** — understand what *isn't* in the prediction path and why
3. **[wood-quality-scale-inversion.md](data-integrity/wood-quality-scale-inversion.md)** — the data-model conventions you'll encounter immediately
4. **[sparse-competitor-data-fallback.md](data-integrity/sparse-competitor-data-fallback.md)** — why eligibility filtering exists
5. **[prompt-feature-parity.md](best-practices/prompt-feature-parity.md)** — how features and prompts must move together
6. **[judge-ui-simplicity-principle.md](best-practices/judge-ui-simplicity-principle.md)** — the UX philosophy for the judge-facing CLI

Then browse the rest as needed when you touch the relevant area.

---

## Cross-repo knowledge

STRATHMARK (the sister repo that owns all handicap calculation) has its own `docs/solutions/` directory. Cross-repo topics live there:

- Absolute variance model (±3s across all competitors)
- Tournament result weighting (97% same-tournament / 3% historical) and the `num_tournament_rounds >= 4` gate
- Decay-weights date-type mismatch bug
- Timeout results polluting baseline
- Ollama cascade hang on unreachable host
- SQLite / Supabase dual-store design

When a topic is owned by STRATHMARK, STRATHEX's docs link across rather than duplicate. Check [github.com/SquirmyWormy275/STRATHMARK](https://github.com/SquirmyWormy275/STRATHMARK) for the upstream docs.

---

## Adding new docs

New entries are written by `/ce:compound` after a problem is solved. The workflow is:

1. Solve the problem (fix the bug, land the refactor, ship the feature)
2. Run `/ce:compound` to capture the solution while context is fresh
3. The skill writes a properly-frontmattered doc under the matching category
4. Update this README's category tables if a new doc adds rows

Don't write solution docs by hand — use the skill so the frontmatter and section structure stay consistent with the knowledge store as a whole.

For maintenance (refreshing stale entries, consolidating overlapping docs, deleting obsolete guidance), use `/ce:compound-refresh`.
