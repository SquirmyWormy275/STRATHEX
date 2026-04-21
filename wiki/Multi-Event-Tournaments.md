# Multi-Event Tournaments

A tournament **day** — multiple independent events, each with their own wood, competitors, format, and rounds. This is what Missoula Pro-Am and Mason County Qualifier look like: five or six distinct events running sequentially on the same program.

Main Menu → **Option 2 (Design a Tournament)**.

---

## What counts as "multi-event"?

Each event has:
- Independent wood config (different species / diameter / quality per event)
- Independent competitor roster
- Independent format (heats→finals or heats→semis→finals)
- Independent event type (Handicap or Championship — see below)
- Independent payout structure
- Independent scheduling

So a tournament day might look like:

```
Event 1: 225mm Standing Block (Open Handicap) — 12 competitors, heats→finals
Event 2: 300mm Underhand       (Open Handicap) — 14 competitors, heats→semis→finals
Event 3: 275mm Standing Block  (Novice Handicap) — 8 competitors, heats→finals
Event 4: 300mm Championship Race (Championship — no handicaps) — 6 competitors
Event 5: 350mm Underhand        (Open Handicap) — 10 competitors, heats→finals
```

Each is configured independently, schedules are laid out, and results roll up into a tournament-wide summary.

---

## Event types

### Handicap events (default)

The standard. STRATHEX calculates marks, runs Monte Carlo, applies tournament weighting across rounds — all the machinery covered in [Tournament Workflow](Tournament-Workflow).

### Championship events

A special mode for "race to the finish" events where handicaps are **not** used:

- Every competitor gets **Mark 3** (same start)
- Fastest raw time wins
- No AI prediction or Monte Carlo validation needed (though you can still run the simulation if curious)
- Approval is simplified — no manual adjustments to make
- Tournament weighting does *not* apply (all marks stay at Mark 3 across rounds)

Championship events bypass prediction calculation entirely. They're configured faster and run simpler. Useful for:
- Open finals where the promoter wants a fastest-cutter result
- Exhibition events
- Pro-only events where everyone's skill is already equalized

Event type is selected during configuration and defaults to `handicap` for backward compatibility.

---

## The flow

```
Main Menu → Option 2
    │
    ▼
1. Enter tournament name + date
2. Enter number of events
3. FOR EACH EVENT:
   a. Configure event (name, code, wood, type, format, stands)
   b. Select competitors
   c. (If handicap) Calculate + approve marks
   d. (If championship) Auto-assign Mark 3 to all
4. Generate master schedule (all heats across all events)
5. Sequential results entry
   — Auto-advances to next incomplete round in next event
6. Final tournament summary (top 3 per event, total earnings per competitor)
7. Save + exit
```

Auto-save fires after major operations: adding an event, generating schedule, recording results.

---

## Event-aware HeatIDs

Because multiple events share the same `Results` sheet, HeatIDs encode both the event and the round:

```
Format: <EVENT_CODE>-<EVENT_NAME>-<ROUND_NAME>

Examples:
  SB-225MM-HEAT1        ← 225mm SB, Heat 1
  UH-300MM-SEMIFA       ← 300mm UH, Semi-Final A
  SB-275MM-NOV-FINAL    ← 275mm SB Novice, Final
  UH-CHAMP-300MM-FINAL  ← 300mm Championship, Final
```

This keeps cross-event analytics clean: you can pull all `UH-300MM-*` records and see a competitor's progression through that event's rounds without pulling data from other events in the same carnival.

---

## State model

`multi_event_tournament_state`:

```python
{
    'tournament_mode': 'multi_event',
    'tournament_name': 'Missoula Pro-Am 2026',
    'tournament_date': '2026-07-04',
    'total_events': 5,
    'events_completed': 2,
    'current_event_index': 2,
    'events': [
        {
            'event_id': 'E001',
            'event_name': '225mm SB',
            'event_order': 1,
            'event_type': 'handicap',    # or 'championship'
            'status': 'completed',        # pending, configured, ready, in_progress, completed
            'wood_species': 'Cottonwood',
            'wood_diameter': 225,
            'wood_quality': 5,
            'num_stands': 4,
            'format': 'heats_to_finals',
            'all_competitors': [...],
            'rounds': [...],              # same structure as single-event
            'handicap_results_all': [...],
            'payout_config': {...},       # if configured
            'final_results': {
                'first_place': 'Cole Schlenker',
                'second_place': 'Eric Hoberg',
                'third_place': 'David Moses Jr.',
                'all_placements': {...},
            },
        },
        # ... more events
    ],
}
```

Each `events[i]` is a full tournament state in miniature.

---

## Tournament weighting scope

Tournament weighting (97%/3% same-wood blend) applies **within each event only**. If the same competitor runs both a 225mm SB and a 300mm UH event, the UH prediction will never use the SB heat result — different wood, different event, different cutting motion entirely.

This is intentional. Two UH semifinals can share a heat-result lineage because the wood and event are the same. Two different *events* can't.

---

## Sequential workflow

After the schedule is generated, the results-entry screen auto-advances through the tournament in event order:

```
Event 1 / 5: 225mm SB
  Heat 1 [in progress] ← enter here
  Heat 2 [pending]
  Heat 3 [pending]
  Final  [pending]

Event 2 / 5: 300mm UH
  ... waiting for Event 1 completion
```

Once Heat 1 is entered, the UI jumps to Heat 2 automatically. Once all heats complete, it jumps to the final. Once the event completes, it jumps to Event 2. The judge never has to navigate manually — just enter times and move on.

This is the key UX improvement over managing five separate single-event tournaments: sequential, auto-advancing, always knows where you are.

---

## Tournament summary

After the last event:

```
TOURNAMENT SUMMARY — Missoula Pro-Am 2026 (July 4, 2026)

┌───────────────────────────────────────────────────────────────────┐
│ EVENT 1: 225mm SB (Open Handicap)                                 │
│   1st  Cole Schlenker      12.3s    $550                          │
│   2nd  Eric Hoberg          12.8s    $350                          │
│   3rd  David Moses Jr.      13.1s    $250                          │
├───────────────────────────────────────────────────────────────────┤
│ EVENT 2: 300mm UH (Open Handicap)                                 │
│   1st  Cody Labahn          26.4s    $550                          │
│   2nd  Erin LaVoie          26.8s    $350                          │
│   3rd  Cole Schlenker       27.1s    $250                          │
├───────────────────────────────────────────────────────────────────┤
│ ... (three more events)                                           │
└───────────────────────────────────────────────────────────────────┘

EARNINGS LEADERBOARD (all events combined)
  1. Cole Schlenker    $1,350  (1st × 1, 2nd × 1, 3rd × 2)
  2. Cody Labahn       $1,100  (1st × 2)
  3. Eric Hoberg         $900  (2nd × 1, 3rd × 1, 4th × 1)
```

Payouts are configured per-event and aggregated across the tournament. Tie-breakers default to the AAA rule of "same time = same payout for both" (see the payout UI for options).

---

## Loading and resuming

A multi-event tournament saves to a single JSON file with all events embedded. You can:
- Save mid-tournament (auto-save triggers after each round)
- Load via Main Menu → Option 6
- Resume exactly where you left off

This matters for multi-day tournaments or for recovery from a laptop crash.

---

## Further reading

- [Tournament Workflow](Tournament-Workflow) — the single-event flow (each event in a multi-event is an instance of this)
- [Bracket Tournaments](Bracket-Tournaments) — alternative format for individual events
- [`woodchopping/ui/multi_event_ui.py`](https://github.com/SquirmyWormy275/STRATHEX/blob/main/woodchopping/ui/multi_event_ui.py) — implementation (~1075 lines)
