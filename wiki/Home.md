# STRATHEX

**Data-driven handicap and tournament-management system for competitive woodchopping.**

STRATHEX combines historical performance analysis, XGBoost machine learning, and LLM-assisted reasoning to produce defensible handicap marks that give every axeman an equal shot at winning — regardless of skill. It runs full multi-round, multi-event tournaments; validates fairness with 2 million Monte Carlo races; and leaves the final call where it belongs: with the official handicapper.

As of V6.0, all calculation is delegated to the sister engine [**STRATHMARK**](https://github.com/SquirmyWormy275/STRATHMARK). STRATHEX is the tournament manager; STRATHMARK is the reusable handicap core.

---

## The short version

A world-champion axeman cuts a 300mm Standing Block in ~25 seconds. A skilled amateur takes ~60 seconds. Put them in the same heat with no handicap and the amateur has zero chance — so no amateur competes, and no tournament happens.

Handicapping fixes this by **delaying the faster competitors' starts** so everyone should finish together. The slowest predicted competitor gets **Mark 3** (starts immediately on the count of "3"); a competitor predicted 15s faster gets **Mark 18** (waits 15 extra seconds); and so on. When predictions are accurate, the race is decided by who actually cuts the wood fastest *today*, not who is most skilled overall.

STRATHEX's job is **predicting the time** as accurately as possible. Everything else — the mark formula, the floor of 3, the 180-second time limit — comes straight from the [AAA Competition Rules](AAA-and-QAA-Rules-Compliance).

---

## Wiki index

### Getting started
- [Quick Start](Quick-Start) — Install, prerequisites, first tournament
- [Architecture](Architecture) — STRATHEX + STRATHMARK layout
- [Ecosystem](Ecosystem) — How this fits with STRATHMARK and Missoula-Pro-Am-Manager

### How it works
- [Handicap System Explained](Handicap-System-Explained) — The full pipeline, in plain English
- [Prediction Methods](Prediction-Methods) — Baseline, XGBoost, LLM
- [Monte Carlo Fairness](Monte-Carlo-Fairness) — Why simulation matters
- [AAA and QAA Rules Compliance](AAA-and-QAA-Rules-Compliance) — What STRATHEX follows, where it deviates, and why

### Running tournaments
- [Tournament Workflow](Tournament-Workflow) — Heats → Semis → Finals
- [Multi-Event Tournaments](Multi-Event-Tournaments) — Full tournament days
- [Bracket Tournaments](Bracket-Tournaments) — Single / double elimination
- [Championship Simulator](Championship-Simulator) — Equal-start race prediction

### Reference
- [Data Model](Data-Model) — Excel sheets, SQLite ResultStore
- [FAQ](FAQ) — Common questions
- [Troubleshooting](Troubleshooting) — Common errors
- [Development](Development) — Contributing, tests, CI
- [Version History](Version-History) — Release notes

---

## Production use

STRATHEX is being considered for use at:
- **[Missoula Pro-Am](https://www.missoulaxe.com/)** (Missoula, MT)
- **Mason County Western Qualifier** (Mason County, WA)
- Any AAA-sanctioned chopping carnival

The engine is tested against 150+ years of Australian handicapping data via the [Queensland Axemen's Association](http://www.qaa.org.au/) empirical scaling tables.

---

**License:** Academic project · **Author:** Alex Kaper · **AI assistance:** Claude (Anthropic)
