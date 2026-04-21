# FAQ

---

## General

### What does STRATHEX stand for?

STRATHEX is an NSA/SAP-style compound codename. The exact decomposition is deliberately opaque (cyberpunk aesthetic, consistent with the related projects STRATHMARK, CODEFRAME, IRONLOGIC, VOIDLOCK). Treat it as a proper noun.

### Is this a replacement for a human handicapper?

**No.** STRATHEX is decision-support software. The Handicapper is the authority (AAA Rule 14). STRATHEX provides evidence — predictions, fairness analysis, audit trails — and the Handicapper approves, overrides, or rejects.

### Can I use this at non-AAA events?

Yes. STRATHEX doesn't enforce AAA membership or registration. The rules it implements (3s floor, 180s ceiling, nearest-second rounding) are conservative defaults that most competitive formats agree with. If your event uses different rules, see [AAA and QAA Rules Compliance](AAA-and-QAA-Rules-Compliance) for what's configurable.

### What sports beyond woodchopping could this handle?

Anything where:
1. Historical performance predicts future performance
2. Multiple factors affect outcome (equipment, conditions, skill)
3. Fair competition requires equalizing start times or scores

Plausible candidates: swimming, track cycling time trials, rowing. Not suitable: team sports, subjective-scoring events, events without reliable time records.

---

## Installation & Running

### Do I need Ollama?

**No, but it helps.** Without Ollama, the LLM prediction layer is unavailable and fairness assessments fall back to statistical summaries. The Baseline and ML predictors still work fully. You're giving up some prediction nuance and pre-race narrative, not core functionality.

If you want it: install Ollama, pull `qwen2.5:7b`, run `ollama serve`. STRATHEX auto-detects.

### Why Python 3.13?

Modern typing, `match`/`case` syntax, and the performance improvements from 3.11+ were all too valuable to give up. STRATHEX uses them heavily.

### Can I run this on a Raspberry Pi at the venue?

Probably not well. ML training and 2M Monte Carlo simulations chew through RAM and CPU. A modern laptop is the minimum comfortable target.

### The install says "can't find strathmark" — what now?

`pip install -e .` in STRATHEX should automatically pull STRATHMARK from GitHub. If you're offline or GitHub is blocked:

```bash
git clone https://github.com/SquirmyWormy275/STRATHMARK.git ../STRATHMARK
pip install -e ../STRATHMARK
pip install -e .
```

See [Quick Start § Editable STRATHMARK](Quick-Start#editable-strathmark-for-engine-developers).

---

## Handicapping

### How much history is needed to handicap a competitor?

Minimum **3 historical results** for the specific event (SB or UH). Anything less and the competitor is blocked — STRATHEX refuses to predict from too little data.

- **3–9 records** → LOW confidence, warning shown
- **10+ records** → sufficient, normal confidence

### What if a competitor has never raced?

They can't be handicapped by STRATHEX. Two options:

1. Assign a panel mark by hand (QAA default: 15 for open SB/UH). Enter into the tournament manually.
2. Have them race in 3+ practice or lead-up events to build a baseline before their first sanctioned tournament.

The rulebooks expect this — handicapping requires performance data, and that's not a STRATHEX limitation, it's a sport-level limitation.

### Why does STRATHEX sometimes prefer the baseline over the ML model?

Selection uses **expected-error scoring**, not a fixed priority. The ML model gets penalized when:
- Training data has few examples of the target diameter
- The competitor has few (3–9) ML-eligible records
- The ML prediction disagrees sharply with the baseline and LLM

In those cases, the scaled baseline (using QAA empirical tables) is more trustworthy than an extrapolating ML model. The selector picks whichever has the lowest expected error.

See [Prediction Methods § Selection Logic](Prediction-Methods#selection-logic-v60).

### Can I force a specific prediction method?

Yes. The approval UI allows manual override — you can pick any prediction (baseline / ML / LLM) or enter a custom mark. The override tracker logs the deviation.

### Why are handicaps changing between tournaments?

STRATHEX learns from every result. After a tournament, the new finish times are added to the `Results` sheet and SQLite ResultStore. Next tournament, predictions incorporate that new data. A competitor who's been improving will see their predicted times drop and their marks rise (later start = less delay). This is the correct behavior — it mirrors the QAA green-book penalty/award system with smoother dynamics.

### My mark feels wrong. What do I do?

1. **Check the three predictions.** Do they agree? If not, the data is saying "we're uncertain" — the Handicapper should investigate.
2. **Check the quality rating.** Is the wood really as soft/hard as you entered?
3. **Check the diameter.** Is it a standard size, or a high-variance one?
4. **Check the Monte Carlo fairness.** Does the simulation flag this competitor as a favorite/underdog?
5. **Override.** If after all that the mark still feels wrong, override it. AAA Rule 14 gives you final authority.

---

## Monte Carlo

### Why ±3 seconds?

Because real-world variance is absolute, not proportional. A 30-second chopper and a 60-second chopper both vary by ~3 seconds race-to-race on similar wood. The variance comes from wood grain, knots, technique wobble — none of which scale with predicted time.

We tested proportional variance (±5%) and got 31% win-rate spread. With absolute ±3s: 6.7%. Absolute variance is measurably fairer. See [Monte Carlo Fairness § Why Absolute](Monte-Carlo-Fairness#why-absolute-variance).

### How many simulations should I run?

- **Handicap fairness validation:** 500K is plenty. Runs in ~1 second.
- **Championship simulator:** 2M (default) for high-resolution win probabilities and percentile distribution.
- **Don't go below 100K** — results get noisy and spurious "biases" appear from random sampling.

### What's a good win-rate spread?

```
< 2%   Excellent — handicaps are essentially perfect
< 4%   Very Good — fair for any practical purpose
< 6%   Good — minor bias; acceptable
< 10%  Fair — noticeable favorite; review marks
> 10%  Poor — systematic bias; predictions are off
```

Most STRATHEX handicap sets come in at 2–4% (Very Good). 10%+ is rare and usually signals a data-quality issue.

---

## Data

### Where does the data live?

- **Canonical (judge-facing):** `woodchopping.xlsx` at the project root. Edit this.
- **Engine substrate:** `~/.strathmark/results.db` (SQLite). Mirrored from Excel automatically.

See [Data Model](Data-Model).

### Will editing the Excel break something?

No — but follow the schema. `Results` rows need valid `CompetitorID` (join to `Competitor`), valid `Species` (join to `wood`), uppercase event code (`SB` or `UH`), and ideally a date. STRATHEX validates on load and surfaces errors with row/field context.

### How do I add a new species?

Add a row to the `wood` sheet with at minimum `Species`, `Janka Hardness`, `Specific Gravity`. The other 4 mechanical properties (shear, crush, MOR, MOE) are optional but improve ML accuracy. Restart STRATHEX to pick up the new species.

### How do I clear the SQLite history?

```bash
rm ~/.strathmark/results.db
python MainProgramV5_2.py   # Recreates + migrates from Excel
```

Safe to do — SQLite is always re-hydratable from Excel. You lose nothing that isn't still in the workbook.

---

## Rules & Compliance

### Does STRATHEX follow the AAA rulebook?

Yes, for the handicapping rules it implements (Rules 12–19, 80, 91). It explicitly does *not* implement the X-penalty/award system from QAA §3 — that's a season-level concern and competitors/clubs track it in green books. See [AAA and QAA Rules Compliance](AAA-and-QAA-Rules-Compliance) for a full mapping.

### What about Treefelling or Sawing events?

Out of scope. STRATHEX handles SB and UH only. Adding a new event type is architecturally straightforward but needs training data, which is the practical blocker.

### Can I use this at AAA championships?

STRATHEX is decision-support — the appointed Handicapper still signs off on every mark. Used that way, yes, it can be used at any AAA-sanctioned event. We'd recommend running it alongside the traditional green-book process until the Handicapper is confident in the outputs.

---

## Cross-repo

### What's the relationship to STRATHMARK?

STRATHMARK is the calculation engine. STRATHEX is the tournament manager. They live in separate repos so that other tournament software (Missoula-Pro-Am-Manager, future projects) can depend on STRATHMARK without pulling in STRATHEX's UI. See [Ecosystem](Ecosystem).

### Can I just use STRATHMARK directly?

Yes — `pip install strathmark`. The Python API is small and the HTTP REST API exposes the same functionality. STRATHEX is optional if you have your own UI/manager.

### I found a bug in the math. Where do I report it?

If it's in predictions, mark arithmetic, Monte Carlo, or fairness assessment → STRATHMARK issue tracker. If it's in the CLI, Excel I/O, tournament workflow, or roster management → STRATHEX issue tracker.

When in doubt, open a STRATHMARK issue — the engine is the source of truth.

---

## Performance

### How long does a handicap calculation take?

- **Baseline only:** <1 second for entire heat
- **Baseline + ML:** ~1 second for entire heat
- **All three methods (Baseline + ML + LLM):** 2–5 seconds per competitor (Ollama-bound)

For an 8-person heat with all three methods: typically 10–15 seconds. Monte Carlo adds another 1–5 seconds.

### Can I make it faster?

If you don't need LLM predictions, skip them — the ML model is usually more accurate anyway and runs in milliseconds. Edit `config.py` or pass `--no-llm` at runtime to disable.

---

## Troubleshooting

See [Troubleshooting](Troubleshooting) for specific errors and fixes.
