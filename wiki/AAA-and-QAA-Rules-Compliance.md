# AAA and QAA Rules Compliance

STRATHEX is a decision-support tool for official handicappers, not a replacement for them. This page maps every STRATHEX behavior to the specific rules from the governing bodies, and is explicit about where the system deviates from convention (and why).

Source documents in the repo:

- [**AAA Competition Rules (Revised August 2024)**](https://github.com/SquirmyWormy275/STRATHEX/blob/main/reference/Competition%20Rules%20AAA%20Updated%20Aug%202024.pdf) — `reference/Competition Rules AAA Updated Aug 2024.pdf`
- [**QAA By-Laws and Handicap Book**](https://github.com/SquirmyWormy275/STRATHEX/blob/main/reference/QAA.pdf) — `reference/QAA.pdf`

Plain-text extracts are in `reference/*.txt` for programmatic reference.

---

## The governing principle

> **AAA Rule 14**: *"The decision of a Committee, or a Handicapper, in respect of a Competitor's handicap is final and may not be challenged, the subject of a Protest or called into question by any person."*

STRATHEX produces a recommendation, supported by evidence (prediction methods, confidence levels, Monte Carlo validation). The Handicapper approves, overrides, or rejects. Manual overrides are always allowed and are tracked (V5.0+ Handicap Override Tracker).

> **AAA Rule 13**: *"Handicaps will be determined based on form, inherent ability and performances and such other information as may be deemed by the Committee, or Handicapper, to be relevant."*

STRATHEX operationalizes "form" (time-decay weighting, recent emphasis), "inherent ability" (historical mean), and "performances" (full results history). The Handicapper provides the "other information" — injuries, training status, equipment changes — via manual overrides.

---

## AAA Competition Rules — what STRATHEX implements

### Rules 12–19 — Handicapping

| Rule | Requirement | STRATHEX implementation |
|---|---|---|
| **12** | Handicap at discretion of Committee/Handicapper | Produces recommendations; Handicapper approves via UI |
| **13** | Based on form, ability, performances, other info | Time-decay + ML/LLM/Baseline predictions; manual override for "other info" |
| **14** | Handicapper's decision is **final** | Manual override always available; no challenge mechanism in the software |
| **15** | Publicize information on a notice board | Out of scope for STRATHEX; judges print/display marks separately |
| **16** | Handicap may be adjusted at any time | Marks can be overridden at any point before results are entered |
| **17** | Calculated to the **nearest second** | ✅ `mark = 3 + round(gap)` using banker's rounding (half-to-even) |
| **18** | Minimum handicap is **3 seconds** | ✅ Hard floor — `mark = max(3, computed_mark)` |
| **19** | Competitor's responsibility to know handicap | Displayed in approval UI; printed in schedule output |

### Rule 80 — Starting

> *"(a) The commencement of which a Championship event / Relay is to commence on is to be the count of 3."*

STRATHEX calls marks starting from 3 — consistent with this rule. The starter calls "Axemen ready... 3!" as the first audible cue; the front marker starts on "3". Subsequent marks are called in order.

### Rule 91 — Time Limits

> *"(a) the Judge has a discretion to direct a Competitor in any Event to cease competing after 2 minutes from the Start Time... (b) a Competitor who has not completely severed his log within 3 minutes from the Start Time may be directed by the Judge to cease chopping or sawing."*

STRATHEX enforces a **180-second hard ceiling**:

```python
mark_ceiling = 180 + 3  # 180s time limit + 3s minimum mark = 183
```

Mark 183 is theoretical — anyone predicted that much faster than the front marker would start as the 3-minute bell rings. In practice, real open-handicap fields never reach this.

### Rules 63–64 — Log Specifications

STRATHEX's approved-diameter list matches AAA Rule 64: *"250mm, 275mm, 300mm, 325mm, 350mm, 375mm, 400mm, 450mm, 500mm, 600mm and 750mm."*

Non-standard diameters (254mm, 270mm, 279mm, etc.) trigger a high-variance warning — they're not AAA-approved measurements and produce predictions with wider expected finish spreads.

Diameter tolerance: AAA Rule 63(b) allows ±2mm (±1mm for championships). STRATHEX doesn't enforce tolerance — that's the log-prep team's job — but the QAA scaling tables implicitly account for small tolerance variance.

---

## QAA By-Laws — what STRATHEX references

### §1 — Handicap Book

> *"For members of the Queensland Axemen's Association (QAA) all performances for woodchopping events will be recorded in a 'green' handicap book."*

STRATHEX does **not** replace the green book. Competitors are responsible for their own handicap books; STRATHEX only reads and predicts, it doesn't assign official handicaps or track the penalty/award system.

### §2 — Panel Marks

STRATHEX falls back to these when all predictions fail:

| Event | QAA Panel Mark | Used in STRATHEX |
|---|---|---|
| Underhand & Standing Events | 15 | ✅ (open events) |
| Treefelling | 70 | Not implemented (tree felling out of scope) |
| Novice | 35 | ✅ (when configured as novice) |
| Junior Events | 15 | ✅ (when configured as junior) |
| Sawing Events | 15 | Not implemented (sawing out of scope) |
| Women's Underhand | 35 | ✅ (when configured) |
| Veterans | Set by committee | Not implemented — requires per-competitor override |

### §3 — Penalties and Awards ("X" system)

> *"Axemen competing off a handicap of 3 and have accumulated X's for their unplaced events shall forfeit all X's once they win more than $60 prize money..."*

**STRATHEX does NOT implement the QAA penalty/award system.** This is a deliberate design choice:

- The X-accumulation and prize-money penalty system is part of the long-term QAA handicap book (updated across a whole competition season)
- STRATHEX operates at the event/tournament level — it's not the right layer to track season-long handicap evolution
- Competitors and their clubs maintain green books independently
- Judges entering results into STRATHEX can cross-reference against the green book for the canonical current mark

**What STRATHEX does instead:** uses performance data (the same underlying information the X system is encoding) to predict form via the prediction engine. A competitor who's been losing consistently will have their baseline creep up in historical data; time-decay ensures recent form dominates. The end effect is similar to the X-award system, just expressed as a smooth time-decay rather than discrete second-lifts.

### §12 — Guide for Drawing up Handicap Heats

STRATHEX uses the QAA heat-drawing grid (§12, p. 8) for heat composition:

**3-heat example:**
```
S/B Heat 1    S/B Heat 2    S/B Heat 3
Axeman #1     Axeman #2     Axeman #3
Axeman #6     Axeman #5     Axeman #4
Axeman #7     Axeman #8     Axeman #9
Axeman #12    Axeman #11    Axeman #10
Axeman #13    Axeman #14    Axeman #15
```

Rankings are determined by predicted time (STRATHEX's interpretation of "highest ranked"), producing heats with one top competitor, one upper-mid, one lower-mid, and one bottom — balanced across heats.

### QAA Diameter Scaling Tables

STRATHEX's diameter scaling uses QAA empirical tables rather than a formula. Three tables (Hardwood, Medium, Softwood), with interpolation between them based on effective Janka hardness. See [Handicap System Explained § Stage 3](Handicap-System-Explained#stage-3--predict-cutting-time) and [`docs/QAA_INTERPOLATION_IMPLEMENTATION.md`](https://github.com/SquirmyWormy275/STRATHEX/blob/main/docs/QAA_INTERPOLATION_IMPLEMENTATION.md).

These tables encode 150+ years of Australian competition data and are more reliable than any formula-based approach. When a diameter is scaled, the approval UI flags it (`* = scaled`) and the confidence is downgraded one tier.

---

## Where STRATHEX deviates from convention (and why)

### Mark ceiling: 183s vs. QAA's 43s

**QAA bylaw §3.1:** *"Maximum handicap 43 seconds in a 300mm diameter underhand or standing block."*

**STRATHEX ceiling:** 183 seconds.

Why the gap?
- QAA's 43s cap works because QAA handicaps a tight pro-level competitor pool. Everyone's on the green book; everyone's been refined through the penalty/award system; the spread is narrow.
- STRATHEX is used for AAA-sanctioned events with much wider skill spreads (pro, novice, amateur, exhibition). Missoula Pro-Am's field includes world-class pros alongside skilled amateurs whose times genuinely vary by 30+ seconds. Capping at 43s would force artificial compression and break the fairness model.
- AAA Rule 91(b)'s 3-minute time limit gives the theoretical ceiling (180s + 3s floor = 183s).

**If you need QAA-style compression:** the STRATHMARK `config.py` exposes `MARK_CEILING` as a frozen dataclass field. Override it per-tournament via STRATHMARK's config API.

### Rounding: half-to-even vs. round-up

**AAA Rule 17:** *"Handicaps are to be calculated to the nearest second."*

Both "round half-to-even" (banker's rounding) and "round half-up" produce results "to the nearest second" — they differ only on exact half-seconds. STRATHEX (V6.0) uses Python's default `round()`, which is **half-to-even**. This avoids systematic upward bias across thousands of mark calculations.

Legacy STRATHEX V5.2 used `ceil()` (always round up). V6.0's switch is a behavior change; see [Version History § V6.0](Version-History#v60-mar-2026).

### No penalty/award system

Covered above — STRATHEX operates at the event level, not the season level. Clubs maintain the green book.

### No sawing / tree felling events

Out of scope. STRATHEX handles Standing Block (SB) and Underhand (UH) only. The engine is generic enough to add other event types (3-board jigger is a known roadmap item), but requires training data — which is the real blocker.

### Wood quality beyond species hardness

STRATHEX uses a judge-assessed **0–10 quality scale** on top of species baseline. This is STRATHEX-specific — neither the AAA nor QAA rulebooks mandate a quality rating. It's a practical addition: a judge's sense of "this Cottonwood is firmer than usual" matters enormously to cutting time, and the rulebooks implicitly account for it through handicapper discretion.

---

## Accountability and transparency

Every handicap STRATHEX produces can be traced:

- **Prediction sources** — which historical records contributed, their weights, their dates
- **Method selection** — which predictor won and why (expected-error score)
- **Scaling provenance** — which QAA table, which diameter conversion
- **Manual overrides** — logged in the Override Tracker with before/after values
- **Monte Carlo validation** — win-rate distribution, fairness rating

If a protest is lodged (AAA Rule 201–207), the Handicapper can produce a full audit trail: "Here's why Joe Smith got Mark 15; here's the data, here's the method, here's the fairness validation. The decision was mine, per Rule 14."

---

## Summary table

| Governing rule | Location | STRATHEX status |
|---|---|---|
| AAA Rule 14 — Final decision | AAA Rulebook p. 6 | ✅ Manual override always available |
| AAA Rule 17 — Nearest second | AAA Rulebook p. 6 | ✅ Python `round()` half-to-even |
| AAA Rule 18 — Min mark = 3 | AAA Rulebook p. 6 | ✅ Hard floor |
| AAA Rule 80 — "Count of 3" start | AAA Rulebook p. 11 | ✅ Mark 3 is front marker |
| AAA Rule 91 — 3-min time limit | AAA Rulebook p. 12 | ✅ Implicit ceiling of 183 |
| AAA Rule 63 — Log diameters | AAA Rulebook p. 9 | ✅ Approved sizes match |
| QAA §2 — Panel marks | QAA p. 2 | ✅ Used as last-resort fallback |
| QAA §3 — X-system / penalties | QAA p. 2–4 | ❌ Not implemented (scope decision) |
| QAA §12 — Heat grid | QAA p. 8 | ✅ Followed for heat composition |
| QAA — Diameter scaling tables | QAA (appendix) | ✅ Full implementation with interpolation |

---

## Further reading

- [AAA Competition Rules PDF](https://github.com/SquirmyWormy275/STRATHEX/blob/main/reference/Competition%20Rules%20AAA%20Updated%20Aug%202024.pdf)
- [QAA By-Laws PDF](https://github.com/SquirmyWormy275/STRATHEX/blob/main/reference/QAA.pdf)
- [Handicap System Explained](Handicap-System-Explained) — how STRATHEX implements Rules 12–19 mechanically
- [Prediction Methods](Prediction-Methods) — the "form, ability, performances" interpretation (Rule 13)
