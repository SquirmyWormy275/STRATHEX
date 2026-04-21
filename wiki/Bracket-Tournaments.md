# Bracket Tournaments

Head-to-head elimination format. Available inside a single event (Option 1 → format selection). Two variants: single elimination and double elimination.

**View-only mode** — bracket results are **not** saved to Excel. This is intentional; brackets are typically exhibition/fun events rather than record-book competitions.

---

## When to use a bracket

| Format | Best for | Example |
|---|---|---|
| **Single Elimination** | Fast show-format finals, crowd-facing entertainment | 8-person pro shootout |
| **Double Elimination** | Serious competitions where nobody gets eliminated on a single bad cut | Qualifier events where fairness matters |
| **Standard (heats→finals)** | Everything else — the AAA default | Regular open handicap events |

---

## Single Elimination

Traditional knockout. Lose once, you're out.

```
Round 1     Quarterfinals    Semifinals     Final
  A ─┐
     ├── W1 ─┐
  H ─┘      │
            ├── SF1 ─┐
  D ─┐      │        │
     ├── W2 ─┘        │
  E ─┘                │
                      ├── CHAMP
  C ─┐                │
     ├── W3 ─┐        │
  F ─┘      │         │
            ├── SF2 ──┘
  B ─┐      │
     ├── W4 ─┘
  G ─┘
```

### Bye placement

Non-power-of-two competitor counts get byes in the first round. Top seeds always get byes (standard tournament practice). The formula:

```
num_byes = next_power_of_2(num_competitors) - num_competitors
first_round_matches = (num_competitors - num_byes) / 2
```

Example: 13 competitors → next power of 2 is 16 → 3 byes → 5 first-round matches. Seeds 1, 2, 3 get byes and auto-advance to the quarterfinals.

---

## Double Elimination

Losers get a second chance through the **losers bracket**. Winners bracket winner must beat losers bracket winner in the **Grand Finals**.

```
Winners:   R1 → R2 → R3 → W.Finals ─┐
                                     ├── Grand Final ── CHAMP
Losers:    drops from W. rounds ──► L.Finals ─┘
```

First-time losers drop to the losers bracket. Lose again → eliminated. Losers bracket winner has to beat the winners bracket winner once (some rules require twice — STRATHEX follows the once-suffices standard).

### Winners bracket

Same as single elimination. Loser drops to the losers bracket rather than being eliminated.

### Losers bracket

Auto-populated as competitors lose their winners-bracket matches. Complex placement logic (standard double-elim bracket math — STRATHEX handles it automatically).

### Grand finals

Winners-bracket champion vs. losers-bracket champion. Single race decides it.

---

## AI-powered seeding

Bracket seeds are generated using the same prediction engine as handicaps ([Prediction Methods](Prediction-Methods)):

- **Seed 1** = competitor with the fastest predicted time
- **Last seed** = competitor with the slowest predicted time
- Top seeds are distributed so they don't meet until the final rounds

This is different from handicap mode, where fastest predictions get *higher* marks (longer delays). In brackets, faster predictions get *better* seeds (deeper placement, more byes).

Seeding happens once — at bracket generation — and is locked for the tournament.

---

## The menu

Bracket mode replaces the normal tournament menu with:

```
1. Select Competitors for Event
2. Configure Event Payouts (Optional)
3. Reconfigure Wood Characteristics    ← only before bracket generation
4. Generate Bracket & Seeds
5. View ASCII Bracket Tree
6. Export Bracket to HTML              ← opens in browser
7. Enter Match Result
8. View Current Round Details
9. Save Event State
10. Return to Main Menu
```

Option 3 is locked after option 4 — wood changes after seeding would invalidate seed assignments.

---

## Match result entry

```
MATCH R1-M3 — Quarterfinal

Seed 3  David Moses Jr.  vs.  Seed 6  Bob Wilson

Enter finish times:
  David Moses Jr.  [28.4]
  Bob Wilson       [31.2]

Winner: David Moses Jr. (28.4s)
Advances to: SF-M2
```

Advancement is automatic. The next match where the winner slots in is populated with their name; the losers-bracket drop (if double elim) is also populated automatically.

---

## Viewing the bracket

### ASCII tree (Option 5)

CLI-friendly. Looks like the diagrams above with competitor names and times filled in. Fast, always works.

### HTML export (Option 6)

Generates a standalone HTML file with professional styling and opens it in the default browser. Good for projecting at events, embedding in a venue display, or printing a bracket poster.

Example HTML export file: `bracket_<event_name>_<timestamp>.html` in the current directory.

---

## Data model

### Single elimination state

```python
tournament_state = {
    'format': 'bracket',
    'elimination_type': 'single',
    'rounds': [
        {
            'round_number': 1,
            'round_name': 'Quarterfinals',
            'round_code': 'QF',
            'matches': [...],
            'status': 'pending',
        },
        # Semifinals, Final, ...
    ],
    'predictions': {...},       # Seed → prediction
    'total_matches': 7,
    'champion': None,           # Set when grand finals completes
    'runner_up': None,
}
```

### Match object

```python
{
    'match_id': 'R1-M3',       # or 'SF-M2', 'LR3-M1', 'GF-M1'
    'match_number': 3,
    'competitor1': 'David Moses Jr.',
    'competitor2': 'Bob Wilson',
    'seed1': 3,
    'seed2': 6,
    'winner': None,
    'loser': None,
    'time1': None,
    'time2': None,
    'finish_position1': None,  # 1 or 2
    'finish_position2': None,
    'status': 'pending',        # pending, in_progress, bye, completed
    'advances_to': 'SF-M2',
    'feeds_from': [],           # Previous match IDs that feed in
    'bracket_type': 'winners',  # winners, losers, grand_finals (double elim)
}
```

---

## Why bracket results aren't saved to Excel

Brackets are viewed as exhibition/fun events. Saving them to the canonical `Results` sheet would pollute the handicap training data with data that doesn't reflect a realistic race setup — every match has just two competitors, which changes the pacing dynamics compared to 4–6 competitor heats.

If you want bracket data in the engine's training set, the recommendation is: don't. Keep the bracket for show events and let the training data come from standard-format races.

---

## Implementation

- [`woodchopping/ui/bracket_ui.py`](https://github.com/SquirmyWormy275/STRATHEX/blob/main/woodchopping/ui/bracket_ui.py) — ~1,950 lines
- Handles bracket generation, bye placement, match advancement, ASCII rendering, HTML export
- No direct STRATHMARK dependency for bracket logic — reuses the prediction engine for seeding only

---

## Further reading

- [Tournament Workflow](Tournament-Workflow) — the standard multi-round format
- [Championship Simulator](Championship-Simulator) — related but different (equal-start, no bracket, Monte Carlo analysis)
