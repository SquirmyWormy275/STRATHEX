# Tournament Workflow

The standard single-event flow: one event, multiple rounds, one champion. This page walks through the judge's session from start to finish.

For tournament *days* with multiple events, see [Multi-Event Tournaments](Multi-Event-Tournaments). For single/double elimination, see [Bracket Tournaments](Bracket-Tournaments).

---

## The happy path

```
Main Menu → Option 1 (Design an Event)
    │
    ▼
1. Configure wood
2. Configure tournament (stands, format, event name)
3. Select competitors
4. Calculate handicaps  ── view Monte Carlo fairness (optional)
5. Approve handicaps    ── manual overrides allowed
6. Generate heats       ── capacity-balanced, skill-balanced
7. Record heat results  ── per-heat entry
8. Select advancers     ── who moves to semis / finals
9. Generate next round  ── tournament weighting applied (97%/3%)
10. Repeat 7-9 until final
11. View final results  ── top 3 + payouts if configured
12. Save + exit         ── dual-write to Excel + ResultStore
```

---

## Step-by-step

### 1. Configure wood

Prompted in this order:

| Prompt | Notes |
|---|---|
| Species | Picked from the `wood` sheet. Species not in the database → error (add it first via the wood menu) |
| Diameter (mm) | Standard values: 250, 275, 300, 325, 350. High-variance diameters (254, 270, 275, 279) produce a CoV warning |
| Quality (0–10) | 10 = very soft, 5 = average, 0 = rock hard. Judge's call |

The current wood config is displayed at the top of every subsequent screen so it's always visible.

### 2. Configure tournament

| Prompt | Options |
|---|---|
| Event name | Free-form ("300mm SB Open", "275mm UH Novice", etc.) |
| Event code | `SB` (Standing Block) or `UH` (Underhand) |
| Number of stands | Available chopping stands at the venue. Affects max heat size |
| Format | `heats_to_finals` (two rounds) or `heats_to_semis_to_finals` (three rounds) |

The capacity calculator (`calculate_tournament_scenarios()`) works out viable heat compositions given the stand count and competitor pool.

### 3. Select competitors

The roster screen shows every competitor in the master list with their event-specific history count. Visual flags:

```
  ✓ Cole Schlenker      (UH: 45 results) HIGH confidence
  ✓ Eric Hoberg         (UH: 23 results) HIGH confidence
  ! Bob Wilson          (UH: 7 results)  LOW confidence — WARNING
  X John Smith          (UH: 2 results)  BLOCKED — cannot select
  ✓ Erin LaVoie         (UH: 18 results) HIGH confidence
```

- `✓` selectable, sufficient data
- `!` selectable with low-confidence warning
- `X` blocked — AAA Rule 13 requires performance data; three records is the absolute floor

Competitors new to the sport must run 3+ events before STRATHEX will handicap them. Until then, the Handicapper assigns a panel mark by hand.

### 4. Calculate handicaps

STRATHEX runs the full pipeline ([Handicap System Explained](Handicap-System-Explained)) and displays:

```
HANDICAP RESULTS — 275mm Aspen, Quality 6, Underhand

Competitor        Baseline    ML      LLM      Selected   Mark    Confidence
──────────────────────────────────────────────────────────────────────────────
Eric Hoberg       25.3s*      24.8s   25.5s    25.3s      3       HIGH (scaled)
Cole Schlenker    24.3s       24.1s   24.5s    24.1s      4       HIGH
David Moses Jr.   24.0s*      24.8s   24.2s    24.0s      4       MED (scaled)
Erin LaVoie       22.6s       22.4s   22.7s    22.4s      6       HIGH
Cody Labahn       22.1s*      22.5s   22.2s    22.1s      6       HIGH (scaled)

* = diameter-scaled using QAA tables

Predicted fairness: 0.8s spread [EXCELLENT]
```

- **Baseline / ML / LLM** columns show each method's result (dash if unavailable)
- **Selected** is the prediction the selector chose (lowest expected error)
- **Mark** is the final handicap
- **Confidence** combines method confidence + any scaling penalties

### 5. Monte Carlo fairness (optional)

Run the simulation to validate the handicap set. 500K iterations by default, ~1 second to complete. Output:

```
MONTE CARLO SIMULATION — 500,000 race iterations

Competitor        Win%     Podium%   Mean Finish   StdDev   Consistency
────────────────────────────────────────────────────────────────────────
Eric Hoberg       20.3%    60.4%     58.3s         3.0s     High
Cole Schlenker    19.8%    59.7%     58.4s         3.0s     High
David Moses Jr.   20.1%    60.1%     58.3s         2.9s     High
Erin LaVoie       20.2%    60.0%     58.3s         3.1s     High
Cody Labahn       19.6%    59.8%     58.4s         3.0s     High

Win-rate spread: 0.7% [EXCELLENT]
```

See [Monte Carlo Fairness](Monte-Carlo-Fairness) for the full methodology.

### 6. Approve handicaps

The Handicapper's sign-off. At this point, any mark can be manually adjusted:

```
Approve all marks as calculated? (y/n/o for overrides): o

Enter adjustments (one per line, blank to finish):
  Eric Hoberg: 4      ← promoted from Mark 3 to Mark 4
  Cody Labahn: 5       ← demoted from Mark 6 to Mark 5

Manual overrides applied.
Re-running fairness simulation...
```

Overrides are logged (in V5.0+ via the Handicap Override Tracker) so the Handicapper has a record of every deviation from the algorithmic prediction. AAA Rule 14 explicitly makes the Handicapper's decision final.

### 7. Generate heats

Once marks are approved, STRATHEX lays out heats using the **QAA heat-drawing grid** (§12 of the QAA bylaws):

```
Rank:        1   2   3   4   5   6   7   8   9   10  11  12
Axeman:      A   B   C   D   E   F   G   H   I   J   K   L
                   ↓ distributed across heats ↓

Heat 1:    A,  F,  G,  L  (ranks 1, 6, 7, 12)
Heat 2:    B,  E,  H,  K  (ranks 2, 5, 8, 11)
Heat 3:    C,  D,  I,  J  (ranks 3, 4, 9, 10)
```

Each heat gets one top-skill competitor, one mid-skill, one lower-mid, and one lower-skill — balanced heats, no "heat of death" concentration.

### 8. Record heat results

The results entry screen:

```
HEAT 1 — 275mm Aspen, Quality 6, Underhand

Marks:
  Eric Hoberg     Mark 3    (front marker)
  Cody Labahn     Mark 6
  Bob Wilson      Mark 8
  Cole Schlenker  Mark 4

Enter actual finish times (seconds):
  Eric Hoberg     [30.2]
  Cody Labahn     [27.8]
  Bob Wilson      [32.1] DNF
  Cole Schlenker  [28.9]

Standings:
  1. Cody Labahn      27.8s + 6s delay = 33.8s finish
  2. Cole Schlenker   28.9s + 4s delay = 32.9s finish  ← actual winner
  3. Eric Hoberg      30.2s + 3s delay = 33.2s finish
  --- Bob Wilson      DNF
```

Times are raw cut durations — the starter's "Mark N!" call marks the start of the competitor's clock. Finish position is determined by total elapsed time from "Mark 3!" (including the delay).

### 9. Select advancers

```
Select advancers to Semi-Final A (top 2):
  [x] Cody Labahn      27.8s  (fastest raw)
  [x] Cole Schlenker   28.9s
  [ ] Eric Hoberg      30.2s
  ---  Bob Wilson       DNF
```

STRATHEX suggests top-N by raw time, but the judge can override.

### 10. Generate next round

The magic happens here. When the semi-final handicaps are calculated, STRATHEX **automatically uses the heat results at 97% weight**:

```
Cody Labahn advances from heats to semis.
  Heat result:     27.8s (275mm Aspen, today)
  Historical avg:  29.3s (mixed wood, years ago)

  Semi prediction: (27.8 × 0.97) + (29.3 × 0.03) = 27.8s
  Confidence:      VERY HIGH
```

No judge action needed. The selector picks the tournament-weighted value automatically. The 3% historical blend prevents a single flukey heat from dominating. See [Handicap System Explained § Stage 5](Handicap-System-Explained#stage-5--tournament-weighting-same-wood-optimization).

### 11. Final results

```
FINAL RESULTS — 275mm UH Open

Placement  Competitor        Time     Mark   Payout
─────────────────────────────────────────────────────
1st        Cole Schlenker    26.4s    4      $550
2nd        Cody Labahn       26.8s    6      $350
3rd        Erin LaVoie       27.1s    6      $250
```

Payouts only display if the payout system was configured in step 2 — see [`payout_ui.py`](https://github.com/SquirmyWormy275/STRATHEX/blob/main/woodchopping/ui/payout_ui.py).

### 12. Save and exit

Auto-saves the tournament state as JSON (for `/Load Previous Event` reload) and appends results to:

1. **Excel** `woodchopping.xlsx` → `Results` sheet (HeatID format: `EventCode-EventName-RoundName`, e.g., `UH-275MM-OPEN-HEAT1`)
2. **SQLite** `~/.strathmark/results.db` → `results` table

Both writes are atomic. If the Excel save fails, the ResultStore write is also rolled back.

---

## State model

`tournament_state` dict (partial):

```python
{
    'event_name': '275mm UH Open',
    'event_code': 'UH',
    'num_stands': 4,
    'format': 'heats_to_semis_to_finals',
    'all_competitors': ['Eric Hoberg', 'Cole Schlenker', ...],
    'all_competitors_df': <pandas.DataFrame>,
    'rounds': [
        {'round_name': 'Heat 1', 'round_type': 'heat',
         'competitors': [...], 'handicap_results': [...],
         'num_to_advance': 2, 'status': 'completed',
         'results': {'Cody Labahn': 27.8, ...},
         'advancers': ['Cody Labahn', 'Cole Schlenker']},
        {'round_name': 'Heat 2', ...},
        {'round_name': 'Semi-Final A', ...},
        {'round_name': 'Final', ...},
    ],
    'handicap_results_all': [...],   # All competitors, keyed by name
    'wood_species': 'Aspen',
    'wood_diameter': 275,
    'wood_quality': 6,
}
```

Saved as JSON after each significant operation. Loadable via Main Menu → Option 6.

---

## Tips for judges

- **Review the approval screen carefully.** The three-column view tells you when predictions disagree; that's usually a data-quality flag.
- **Run the Monte Carlo simulation before the first race.** 500K iterations takes a second and catches subtle bias.
- **Use manual overrides sparingly and document them.** The override tracker keeps a log, which matters if anyone questions the marks later.
- **Let tournament weighting do its job.** Don't manually plug in heat results — the system already does this better.
- **Trust the sparse-data blocks.** If STRATHEX refuses to handicap someone, hand-assign a panel mark (15 for open SB/UH) and move on.

---

## Further reading

- [Multi-Event Tournaments](Multi-Event-Tournaments) — running a full tournament day
- [Bracket Tournaments](Bracket-Tournaments) — single/double elimination
- [Handicap System Explained](Handicap-System-Explained) — what happens inside step 4
- [AAA and QAA Rules Compliance](AAA-and-QAA-Rules-Compliance) — which rules shaped each step
