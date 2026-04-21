# The Handicap System, Explained

This page walks through what STRATHEX actually does when you click "calculate handicaps." It covers the theory, the rules it's working under, and the code it runs.

> **The rulebook view.** Handicapping in STRATHEX is entirely governed by a tiny slice of the AAA Competition Rules: **Rules 12–19** (Handicapping) plus **Rule 80** (Starting) and **Rule 91** (time limits). STRATHEX is decision support — the appointed Handicapper has final authority (Rule 14). See the [AAA and QAA Rules Compliance](AAA-and-QAA-Rules-Compliance) page for the full mapping.

---

## What is a handicap?

In competitive woodchopping, skill differences between competitors are enormous. A world-class axeman cuts a 300mm Standing Block in ~25 seconds; a skilled amateur takes ~60. Without handicaps, the amateur has zero chance.

Handicapping solves this by **delaying the faster competitors**. Starts are called by number:

```
"Axemen ready..."
"3!"        ← slowest competitor starts here
"4!"        ← (one second later)
"5!"
...
"18!"       ← a competitor 15s faster starts here
...
"30!"       ← the back marker starts here (27s delay)
```

The mark is the number called. Mark 3 is the **front marker** (slowest prediction, starts immediately). Higher marks are **back markers** (faster competitors, longer delays). If predictions are accurate, everyone finishes together and the race is won by whoever actually cuts fastest *today*.

> The "count of 3" start sequence is the championship/relay convention set by [AAA Rule 80(a)](AAA-and-QAA-Rules-Compliance#rule-80--starting).

## The mark formula

```
gap  = predicted_time(competitor) − predicted_time(front_marker)
mark = 3 + round(gap)                 # round to nearest whole second
mark = min(mark, 183)                  # hard ceiling
```

### Why 3?

[AAA Rule 18](AAA-and-QAA-Rules-Compliance#rules-12-19--handicapping): **"The minimum handicap for a Competitor is 3 seconds."** No lower — ever. The front marker starts on the "Mark 3!" call.

### Why nearest second?

[AAA Rule 17](AAA-and-QAA-Rules-Compliance#rules-12-19--handicapping): **"Handicaps are to be calculated to the nearest second."** STRATHMARK uses standard Python `round()` (banker's rounding, half-to-even) which avoids systematic upward bias. Legacy STRATHEX V5.2 rounded up; the V6.0 engine rounds to nearest — see [Version History](Version-History#v60-mar-2026).

### Why 183?

It's the system ceiling: **180-second time limit** ([AAA Rule 91b](AAA-and-QAA-Rules-Compliance#rule-91--time-limits): "the Judge may direct a Competitor to cease chopping after 3 minutes") plus the 3-second floor. A competitor assigned Mark 183 would start as the 180-second cut-off bell rings — effectively a theoretical boundary. In practice, real-world open handicaps top out well below this.

> **QAA deviation.** QAA bylaws cap the Open Underhand / Standing Block back mark at **43 seconds** for a 300mm block. STRATHEX's 183s ceiling is more permissive — it's designed for the wide skill spread of amateur and novelty events (Missoula Pro-Am, Mason County Qualifier) where QAA's tight-band pro handicaps don't apply.

## The end-to-end pipeline

```
1. Gather competitor history        (Excel Results sheet + SQLite ResultStore)
        │
        ▼
2. Validate data                    (sparse-data gating, outlier detection)
        │
        ▼
3. Predict cutting time             (Baseline · ML · LLM — in parallel)
        │
        ▼
4. Select best prediction           (expected-error scoring)
        │
        ▼
5. Apply tournament weighting       (97%/3% if same-wood heat data exists)
        │
        ▼
6. Compute marks                    (gap → floor 3 → round → ceiling 183)
        │
        ▼
7. Optionally validate fairness     (2M Monte Carlo simulations)
        │
        ▼
8. Judge approval + manual override (AAA Rule 14: final authority)
```

Each stage is explained below.

---

## Stage 1 — Gather history

For each competitor, STRATHEX pulls their full historical results from the `Results` sheet (Excel) and, since V6.0, from the SQLite ResultStore. Records include:

- Event code (`SB` = Standing Block, `UH` = Underhand)
- Raw finish time (seconds)
- Wood species
- Block diameter (mm)
- Wood quality (0–10 scale)
- Heat ID (for tournament context)
- Date (for time-decay weighting)

See [Data Model](Data-Model) for the full schema.

## Stage 2 — Validate data

### Sparse-data validation

Prediction error is a function of how much data you have:

| Sample size | Typical prediction error | Treatment |
|---|---|---|
| N < 3 | 8–12 seconds | **BLOCKED** — competitor cannot be selected |
| 3 ≤ N < 10 | 5–10 seconds | **WARNING** — confidence flagged as LOW |
| N ≥ 10 | 2–4 seconds | **SUFFICIENT** — normal confidence |

This was calibrated against 1,003 historical results. The judge sees inline warnings in the roster picker:

```
WARNING: Low Confidence Predictions
═══════════════════════════════════════
  ! Bob Wilson - Only 7 UH results
  ! Amy Chen - Only 4 UH results

  These competitors CAN be selected, but predictions
  will be less reliable (expect 5-10s error).

BLOCKED COMPETITORS (Cannot be selected)
═══════════════════════════════════════
  X John Smith - Insufficient UH history (N=2)
```

### Outlier detection

Historical results go through a 3×IQR outlier filter before being used. This catches data-entry errors and aborted cuts (axe broken, competitor fell) without removing genuine exceptional performances. IQR (interquartile range) is used rather than standard deviation because it's not itself skewed by outliers.

---

## Stage 3 — Predict cutting time

STRATHEX runs three independent predictors and picks the most accurate for each competitor. Full detail on [Prediction Methods](Prediction-Methods). Short version:

- **Baseline** — statistical time-weighted average with QAA diameter scaling and quality adjustment. Always available.
- **ML (XGBoost)** — 23-feature regression model, separate for SB and UH. Requires ≥30 training records.
- **LLM (Ollama qwen2.5:7b)** — baseline with AI-reasoned quality adjustment. Requires Ollama running locally.

All three use the same time-decay weighting (2-year half-life), so recent performances dominate even for competitors with 7+ year histories.

### Diameter scaling

Block diameter (mm) has an outsized effect on time — a 325mm block takes ~30% longer to cut than a 250mm block of the same species. STRATHEX scales historical times using empirical lookup tables from the **Queensland Axemen's Association** (see [QAA.pdf](https://github.com/SquirmyWormy275/STRATHEX/blob/main/reference/QAA.pdf) in the reference folder).

QAA tables are used instead of a physics-based power-law formula because they're backed by 150+ years of actual competition data. Three tables are maintained — Hardwood, Medium, Softwood — and STRATHEX interpolates between them based on effective Janka hardness (which combines species baseline hardness with the judge-assessed quality rating). See [docs/QAA_INTERPOLATION_IMPLEMENTATION.md](https://github.com/SquirmyWormy275/STRATHEX/blob/main/docs/QAA_INTERPOLATION_IMPLEMENTATION.md).

### High-variance diameter warnings

Some diameters show a coefficient of variation above 60% in historical data:

| Diameter | CoV | Reason |
|---|---|---|
| 279mm | 71% | Uncommon size; mix of wood types dominates |
| 254mm | 67% | Same |
| 270mm | 63% | Same |
| 275mm | 61% | Borderline; still heavily used |

When a judge picks one of these, the wood-configuration screen displays a warning and recommends a standard diameter (250/275/300/325/350mm). The tournament can still proceed; judges just go in eyes-open about wider expected finish spreads.

---

## Stage 4 — Select the best prediction

V6.0 uses **expected-error scoring** rather than a fixed priority cascade. For each method that returned a prediction, STRATHMARK computes:

```
score = base_error(confidence)       # VERY HIGH=2.0, HIGH=3.0, MEDIUM=5.0, LOW=7.0, VERY LOW=9.0
      + 0.5  if method == LLM         # LLM inherently less consistent
      + 1.5  if scaled                # Cross-diameter scaling penalty
      − 1.0  if tournament_weighted   # Same-tournament bonus (floor 0.5)
      + spread_penalty                # +1 or +2 if predictions diverge ≥4s or ≥12%

Lowest score wins.
Manual override always wins.
Panel mark is last resort.
```

This matters because a VERY HIGH confidence LLM prediction should beat a LOW confidence baseline — which the old fixed cascade (Baseline → ML → LLM → fallback) couldn't express.

Each competitor's row in the approval UI shows all three predictions and which one won:

```
Competitor           Baseline    ML      LLM      Selected   Method     Confidence
──────────────────────────────────────────────────────────────────────────────────
Cole Schlenker       24.3s       24.1s   24.5s    24.1s      ML         HIGH
David Moses Jr.      24.0s*      24.8s   24.2s    24.0s      Baseline   MEDIUM (scaled)
Erin LaVoie          22.6s       22.4s   22.7s    22.4s      ML         HIGH

* = diameter-scaled from historical data
```

---

## Stage 5 — Tournament weighting (same-wood optimization)

When STRATHEX generates a second round (semis from heats, finals from semis, or finals direct from heats), it automatically blends today's heat time with historical baseline at a **97% / 3%** ratio:

```python
prediction = (today_heat_time × 0.97) + (historical_baseline × 0.03)
```

**Rationale:** Today's heat result came from the exact same block geometry and wood condition the final will be cut on. Historical data from years ago — different trees, different grain, different competitor form — is nearly useless by comparison. The 3% historical blend prevents a single anomalous heat (equipment failure, slip) from dominating. Confidence upgrades to **VERY HIGH** for any prediction using tournament weighting.

Example:

```
Competitor advances from heats to finals:
  Heat result:          27.1s (same 275mm Aspen block, TODAY)
  Historical avg:       24.5s (different wood, years ago)

  Final prediction:     (27.1 × 0.97) + (24.5 × 0.03) = 27.0s
  Confidence:           VERY HIGH
  (vs. old system:      would have used 24.5s — unfairly fast)
```

This activation is automatic — judges don't opt in. See `extract_tournament_results()` and `calculate_ai_enhanced_handicaps()`.

---

## Stage 6 — Compute marks

Standard arithmetic:

```python
sorted_by_speed = sort(competitors, key=predicted_time, descending=True)
slowest_time = sorted_by_speed[0].predicted_time

for competitor in sorted_by_speed:
    gap = slowest_time - competitor.predicted_time
    mark = 3 + round(gap)
    mark = min(mark, 183)
```

Worked example:

| Name | Predicted | Gap | Mark | Delay at start |
|---|---|---|---|---|
| Sue Johnson | 58.3s | 0.0s | **3** | 0s |
| Bob Wilson | 52.7s | 5.6s | **9** | 6s |
| Amy Chen | 48.2s | 10.1s | **13** | 10s |
| Joe Smith | 42.8s | 15.5s | **18** | 15s |
| Dan Martinez | 38.1s | 20.2s | **23** | 20s |

Theoretical finish times (no variance):

```
Sue:  0s + 58.3s = 58.3s
Bob:  6s + 52.7s = 58.7s
Amy: 10s + 48.2s = 58.2s
Joe: 15s + 42.8s = 57.8s
Dan: 20s + 38.1s = 58.1s
```

Everyone inside ±0.5 seconds — theoretically a coin-flip. Real variance (grain, technique, wood consistency) decides the race.

---

## Stage 7 — Monte Carlo fairness validation

Full detail on [Monte Carlo Fairness](Monte-Carlo-Fairness). Short version:

STRATHMARK runs 500K–2M simulated races with each competitor's time varying by **±3 seconds absolute** (not percentage — see below). Win rates are tracked per competitor:

```
Fairness rating   Win-rate spread
───────────────   ───────────────
Excellent         < 2%
Very Good         < 4%
Good              < 6%
Fair              < 10%
Poor              > 10%
```

The "±3s absolute variance" decision is the biggest methodological bet in the entire system. See [Monte Carlo Fairness § Why absolute](Monte-Carlo-Fairness#why-absolute-variance).

---

## Stage 8 — Judge approval

The approval screen shows the full calculation:

```
HANDICAP RESULTS — 275mm Aspen, Quality 6, Underhand

Competitor        Pred    Gap    Mark   Method    Confidence    Notes
─────────────────────────────────────────────────────────────────────
Eric Hoberg       25.3s   0.0s   3      Baseline  HIGH (scaled) Scaled 325→275
Cole Schlenker    24.1s   1.2s   4      ML        HIGH
David Moses Jr.   24.0s   1.3s   4      Baseline  HIGH (scaled) Scaled 325→275
Erin LaVoie       22.4s   2.9s   6      ML        HIGH
Cody Labahn       22.1s   3.2s   6      Baseline  HIGH (scaled) Scaled 325→275

Predicted fairness:  0.8s spread  [EXCELLENT]
```

Every mark can be manually overridden. The AAA Rulebook is explicit: **"The decision of a Committee, or a Handicapper, in respect of a Competitor's handicap is final and may not be challenged"** ([Rule 14](AAA-and-QAA-Rules-Compliance#rules-12-19--handicapping)). STRATHEX provides evidence; the Handicapper provides the signature.

---

## Data persistence

Once a tournament completes, results are written to:

1. **Excel** `woodchopping.xlsx` → `Results` sheet. Canonical, portable, editable.
2. **SQLite** `~/.strathmark/results.db` → `results` table. Cross-competition history; feeds the next tournament's predictions.

Every save is dual-write and atomic. On startup, STRATHEX runs an idempotent migration from Excel to SQLite (`INSERT OR IGNORE` — safe to re-run).

See [Data Model](Data-Model) for schema details.

---

## Further reading

- [Prediction Methods](Prediction-Methods) — How Baseline, ML, and LLM actually compute times
- [Monte Carlo Fairness](Monte-Carlo-Fairness) — Why ±3 seconds absolute
- [AAA and QAA Rules Compliance](AAA-and-QAA-Rules-Compliance) — Full mapping of STRATHEX to the rulebooks
- [docs/HANDICAP_SYSTEM_EXPLAINED.md](https://github.com/SquirmyWormy275/STRATHEX/blob/main/docs/HANDICAP_SYSTEM_EXPLAINED.md) — Pseudocode and Python for each stage
