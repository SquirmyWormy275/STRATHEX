# Ecosystem

STRATHEX is one of several woodchopping tools that share a single calculation core.

## The stack

```
┌──────────────────────────────────────────────────────────────────┐
│  Tournament management layer                                     │
│                                                                  │
│  STRATHEX            Missoula-Pro-Am-Manager   Future tools      │
│  (full CLI,          (event-specific,          (web apps,        │
│  multi-event,        lightweight)              mobile scoring)   │
│  Excel workflow)                                                 │
│        │                      │                    │             │
│        └──────────────────────┼────────────────────┘             │
│                               ▼                                  │
│  ═══════════════════════════════════════════════════════════     │
│  STRATHMARK                                                      │
│  (pip-installable handicap engine)                               │
│                                                                  │
│  calculator · predictor · variance · wood · decay · fairness    │
│  + FastAPI HTTP layer (for non-Python consumers)                 │
│  ═══════════════════════════════════════════════════════════     │
└──────────────────────────────────────────────────────────────────┘
```

## Projects

### [STRATHEX](https://github.com/SquirmyWormy275/STRATHEX) (this repo)

**Role:** Full-featured tournament management for an AAA-sanctioned chopping carnival.

- Multi-round single events (heats → semis → finals)
- Multi-event tournament days (complete shows — multiple independent events)
- Bracket tournaments (single & double elimination)
- Championship Race Simulator (equal-start predictor, no handicaps)
- Excel I/O for portability with judges' workflows
- Prize-money / payout configuration
- Live-results entry with automatic advancer selection
- AI-powered fairness narration and judge explanations

**Audience:** Tournament organizers, official handicappers, academic/research users.

### [STRATHMARK](https://github.com/SquirmyWormy275/STRATHMARK)

**Role:** The calculation engine. Extracted from STRATHEX for reuse.

- AAA-compliant mark calculation (3s floor, 183s ceiling, nearest-second rounding)
- Full prediction cascade: Manual → LLM → ML → Baseline → Panel fallback
- Expected-error selection (confidence-based scoring, not fixed priority)
- Absolute ±3s variance Monte Carlo (500K–2M iterations)
- QAA empirical diameter scaling (150+ years of Australian data)
- Exponential time-decay (2-year half-life)
- SQLite ResultStore (`~/.strathmark/results.db`) — persists across competitions
- Optional FastAPI HTTP API for web/mobile consumers
- Optional Supabase/PostgreSQL backend for shared deployments

**Audience:** Other tournament managers, scoring apps, analysis tools, research projects.

Install standalone: `pip install strathmark`.

### Missoula-Pro-Am-Manager *(sibling project)*

**Role:** Purpose-built manager for the Missoula Pro-Am. Lighter surface area than STRATHEX.

- Event-day-specific workflow (no full roster management)
- Also depends on STRATHMARK as its handicap core
- Designed for a single laptop at a tent in a sawdust pile

## Why three repos instead of one?

Tournament software lives and dies by trust. A pro-am handicapper has to be able to look at a mark and know *exactly* where it came from. That's easier when:

- The math lives in one small, well-tested package (STRATHMARK has 667+ tests).
- Rule changes happen in one place. When the AAA rulebook updates and the mark floor moves, every downstream tool gets the fix on the next release.
- Each UI can evolve independently without touching the engine. STRATHEX's multi-event CLI and a future web app have completely different needs and shouldn't fight for the same codebase.

## How the repos stay in sync

- **STRATHMARK** publishes releases on GitHub.
- **STRATHEX**'s `pyproject.toml` pins the STRATHMARK `main` branch as a direct dependency. Updates ride along on the next `pip install -e .`.
- Both repos maintain CI on Ubuntu + Windows (ruff, pytest, build verification) and both require a passing matrix before merge.
- Both repos share a wiki scheme — common pages (handicap explanation, AAA/QAA rules) are written once and cross-referenced.

## Upstream references

| Body | Role | STRATHEX references |
|---|---|---|
| [Australian Axemen's Association](https://www.axemen.com.au/) (AAA) | National governing body. Publishes *Competition Rules and Code of Conduct* (August 2024 revision). | Mark floor, maximum time, heat composition, rounding, draw procedure. See [AAA and QAA Rules Compliance](AAA-and-QAA-Rules-Compliance). |
| [Queensland Axemen's Association](http://www.qaa.org.au/) (QAA) | Largest state body. Publishes the *Handicap Book* and panel-mark bylaws. | Panel marks, penalty/award system (tracked by judges, not STRATHEX), heat-drawing grid, diameter scaling tables. |
| Competition traditions | 150+ years of institutional knowledge | Absolute-variance modeling, same-wood tournament weighting, consistency ratings |

## Contributing across repos

- STRATHEX-only change (UI, Excel workflow) → PR against STRATHEX `main`.
- Engine change (mark logic, prediction, Monte Carlo) → PR against STRATHMARK first; STRATHEX picks it up automatically.
- Rule interpretation question → open an issue on STRATHMARK (the engine is the source of truth); cross-reference in STRATHEX if the UI also needs updating.

See [Development](Development) for the local loop.
