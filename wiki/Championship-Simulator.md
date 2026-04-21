# Championship Race Simulator

An analytics tool, not a tournament manager. Answers the question: **"If these competitors all started at the same time, who'd win — and how often?"**

Main Menu → **Option 3**.

No handicaps. No tournament state. No Excel writes. 2 million Monte Carlo simulations. AI-powered race commentary.

---

## What it does

1. Judge configures wood (species, diameter, quality)
2. Picks an event (SB or UH)
3. Picks competitors (no capacity limit — pick as many as you like)
4. STRATHEX generates predictions using the normal engine (Baseline / ML / LLM)
5. Assigns **Mark 3 to every competitor** (equal start)
6. Runs **2 million Monte Carlo simulations**
7. Displays:
   - Championship results table (predicted times, seeds)
   - Per-competitor statistics (mean finish, std_dev, percentiles, consistency)
   - Win-rate distribution
   - AI-generated race analysis

View-only. Nothing gets saved. Nothing gets handicapped. It's a pure *analysis* tool.

---

## Why it exists

Because real championship-format events (Missoula Pro-Am's championship final, exhibition races at Royal Shows) are fundamentally different from handicap races:

- Everyone starts at the same time
- Fastest raw cut wins
- The interesting question isn't "is this fair?" — it's "who's the favorite?" and "who's the dark horse?"

STRATHEX's handicap-focused fairness metrics don't help with this. The Championship Simulator reuses the prediction engine but answers a completely different question.

---

## Example output

### Championship results

```
CHAMPIONSHIP RACE — 300mm Eastern White Pine, Quality 5, Standing Block

Seed  Competitor           Predicted   Method       Confidence
──────────────────────────────────────────────────────────────
1     Cody Labahn          26.2s       ML            HIGH
2     Erin LaVoie          27.8s       ML            HIGH
3     David Moses Jr.      29.4s       Baseline      MED (scaled)
4     Eric Hoberg          34.1s       ML            HIGH
```

### Per-competitor statistics (from 2M sims)

```
Competitor        Win%     Podium%   Mean     StdDev   P25    P50    P75    Consistency
───────────────────────────────────────────────────────────────────────────────────────
Cody Labahn       48.3%    89.2%     26.2s    3.0s    24.2s  26.2s  28.2s  High
Erin LaVoie       29.1%    78.4%     27.8s    3.0s    25.8s  27.8s  29.8s  High
David Moses Jr.   17.4%    55.1%     29.4s    3.1s    27.3s  29.4s  31.5s  High
Eric Hoberg        5.2%    27.3%     34.1s    2.9s    32.2s  34.1s  36.0s  High
```

### AI race analysis

```
CHAMPIONSHIP ANALYSIS

Race favorite: Cody Labahn (48.3% win rate)
  Strong predicted time (26.2s) backed by HIGH confidence ML model. Podium
  near-lock at 89.2% — this race is his to lose.

Dark horse: David Moses Jr. (17.4% win rate)
  Diameter-scaled prediction (325mm → 300mm) carries uncertainty. If his
  scaling is optimistic by even 1.5s, he slots into 2nd. Watch for early
  lead in the first third of the cut.

Key matchup: Labahn vs. LaVoie
  1.6-second gap is tight — within the ±3s variance envelope. Any wood-grain
  luck tips this match. If Labahn hits a knot early, LaVoie walks through.

Consistency: All four competitors rate "High" (std_dev ≈ 3.0s). No wild cards.
The podium order is probably Labahn → LaVoie → Moses, but the race is
closer than the headline win% suggests.

Race excitement rating: 7/10 — clear favorite but realistic upset paths.
```

AI commentary generated via `get_championship_race_analysis()` in `strathmark.fairness`. Requires Ollama; falls back to a statistical summary if unavailable.

---

## How it differs from handicap mode

| Dimension | Handicap mode | Championship simulator |
|---|---|---|
| Start time | Delayed per competitor (Mark N) | Simultaneous (all Mark 3) |
| Goal | Fair competition | Predict outcome |
| Predictions used | To compute marks | To seed the race |
| Monte Carlo | Tests mark fairness | Tests win probability |
| AI output | Fairness assessment | Race commentary |
| Saves to Excel | Yes (Results sheet) | No |
| Tournament state | Yes (auto-save) | No |
| Manual overrides | Yes | No |
| Iterations (default) | 500K | 2M |

---

## What the ±3s variance means here

Same absolute-variance model as handicap fairness ([Monte Carlo Fairness](Monte-Carlo-Fairness)). Each simulated race perturbs each competitor's time by a Gaussian with σ=1.5 (so ±3s is the 2-sigma range).

Over 2 million iterations, this produces high-resolution win probabilities. A competitor predicted 1.5s faster than the next-best typically wins 55–60% of the time (the overlap with the next competitor's variance envelope). A 3s gap produces ~75% win rate. A 6s gap is essentially decisive.

---

## Use cases

- **Pre-event drama.** "Here's how the championship is going to shake out" — shown to the crowd before the race.
- **Competitor self-assessment.** Judge or coach explores "what would I need to cut to make the podium?" by tweaking inputs.
- **Format design.** Promoter sees if a championship field is competitive enough to be interesting (everyone clustered) or needs a handicap (wide spread favoring one competitor).
- **Training analysis.** Compare predicted vs. actual in post-race — how did the simulator's top-3 rank against the result?

---

## Why 2 million simulations?

Overkill for win probability — 100K is enough. But the simulator also tracks:
- Podium probability (top-3 finish rate)
- Full percentile distribution (p5/p25/p50/p75/p95 finish times)
- Consistency analysis (std_dev of finish time)
- Standing-order probabilities (P(A finishes before B))

These are higher-order statistics that need more iterations to stabilize. 2M is the sweet spot for the championship simulator's broader output.

Takes 3–5 seconds on a modern laptop. Memory overhead ~160MB for 10 competitors at 2M.

---

## Implementation

- [`woodchopping/ui/championship_simulator.py`](https://github.com/SquirmyWormy275/STRATHEX/blob/main/woodchopping/ui/championship_simulator.py) — UI flow
- [`strathmark.variance.run_monte_carlo_simulation`](https://github.com/SquirmyWormy275/STRATHMARK/blob/main/strathmark/variance.py) — core Monte Carlo
- [`strathmark.fairness.get_championship_race_analysis`](https://github.com/SquirmyWormy275/STRATHMARK/blob/main/strathmark/fairness.py) — AI commentary

Relies on the same prediction cascade, same time-decay, same QAA scaling as the handicap system. The *only* differences are: equal marks, 2M iterations, commentary prompt instead of fairness prompt.

---

## Further reading

- [Monte Carlo Fairness](Monte-Carlo-Fairness) — the underlying simulation methodology
- [Prediction Methods](Prediction-Methods) — how the times get predicted
- [Bracket Tournaments](Bracket-Tournaments) — related but head-to-head rather than simultaneous
