# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

STRATHEX (Woodchopping Handicap Calculator) is a data-driven tournament management system for woodchopping competitions. It combines historical performance analysis, AI-enhanced prediction modeling (via Ollama), and Monte Carlo simulation validation to create handicaps that give all competitors equal probability of winning, regardless of skill level. The system also includes comprehensive prize money/payout tracking for professional tournaments.

As of **V6.0**, all handicap calculation, Monte Carlo simulation, prediction
aggregation, and AI fairness assessment is delegated to **STRATHMARK**
(https://github.com/SquirmyWormy275/STRATHMARK), a separate pip-installable
engine. STRATHEX retains the tournament management surface (UI, Excel I/O,
multi-round/multi-event flows, payouts, championship simulator). The bridge
between the two is [woodchopping/strathmark_adapter.py](woodchopping/strathmark_adapter.py).

The system implements a critical innovation: absolute variance modeling (±3 seconds for all competitors) rather than proportional variance, ensuring true fairness as real-world factors affect competitors equally in absolute terms.

## Running the Program

```bash
# Install STRATHEX (auto-pulls strathmark from GitHub) and dev tools
pip install -e ".[dev]"

# Run main program
python MainProgramV5_2.py

# Ensure Ollama is running locally for AI predictions
# Default model: qwen2.5:7b (configurable via llm_config.DEFAULT_MODEL)
# Optional: qwen2.5:32b for higher-precision mathematical reasoning
```

**Prerequisites:**
- Python 3.13+
- Ollama running locally with qwen2.5:7b (or qwen2.5:32b) model
- `woodchopping.xlsx` in the project root
- STRATHMARK installed (handled automatically by `pip install -e .`)

## Dependency and Tooling Source of Truth

All runtime/dev dependencies and tool config (pytest, ruff, coverage) live in
[pyproject.toml](pyproject.toml). There is no `requirements.txt`. CI runs lint,
tests, and a build verification on every push/PR to `main` — see
[.github/workflows/ci.yml](.github/workflows/ci.yml) and the README "CI/CD"
section. Tests that need a local Ollama instance must be marked
`@pytest.mark.ollama` so CI can skip them with `-m "not ollama"`.

**Main Menu Options:**
1. Design an Event (Single Event Tournament)
2. Design a Tournament (Multiple Events)
3. **Championship Race Simulator** - Fun predictive tool for race outcome analysis (Analytics section)
4. **View Competitor Dashboard** - Performance analytics for individual competitors (Analytics section)
5. Add/Edit/Remove Competitors from Master Roster
6. Load Previous Event/Tournament
7. Reload Roster from Excel
8. How Does This System Work? (Explanation System)
9. Exit

## ⚠️ CRITICAL DEVELOPMENT RULE - DOCUMENTATION SYNC

**STANDING ORDER (MANDATORY):**

Whenever you make ANY change to the program code, you MUST update the relevant documentation:

### 1. For ALL Code Changes:
- Update technical documentation in `docs/` if functionality changes
- Update `README.md` if user-facing features change
- Update `SYSTEM_STATUS.md` if system capabilities change

### 2. For Prediction Model Changes (ESPECIALLY IMPORTANT):
- **ALWAYS update `explanation_system_functions.py`** (STRATHEX guide)
- Update sections explaining how predictions work
- Add examples showing the new behavior
- Document the improvement in the "System Improvements" section
- Ensure judges understand WHY and HOW changes affect handicaps

### 3. Examples of Changes That Require Documentation:
- ✓ Time-decay weighting formulas
- ✓ Diameter scaling logic
- ✓ Wood quality adjustments
- ✓ Prediction selection priority
- ✓ Feature engineering changes
- ✓ New prediction methods
- ✓ Algorithm parameter changes
- ✓ ANY change that affects handicap calculations

### 4. Documentation Files to Check:
- `explanation_system_functions.py` - Educational wizard (judges read this!)
- `docs/SYSTEM_STATUS.md` - Current capabilities
- `docs/ML_AUDIT_REPORT.md` - ML model documentation
- `README.md` - User-facing guide
- `wiki/*.md` - Judge-facing GitHub Wiki pages (17 content pages). Edit in `wiki/`, then publish with `bash wiki/publish.sh`

### 5. Why This Matters:
**Trust = Understanding**

Judges must understand how the system works to trust its handicaps. Outdated documentation destroys trust. If the code changes but documentation doesn't, judges will notice discrepancies and lose confidence in the system.

**This is NOT optional. Documentation updates are part of the code change, not a separate task.**

## ⚠️ CRITICAL DEVELOPMENT RULE - ASCII ART ALIGNMENT

**STANDING ORDER (MANDATORY):**

All ASCII art banners and box-drawing elements MUST adhere to strict alignment standards. Misaligned borders destroy the professional appearance of the CLI interface.

### 1. Standard Banner Width:
- **Total width: EXACTLY 70 characters per line**
- Border characters (╔╗╚╝║) + 68 characters of internal content
- Top border: `╔` + `═` × 68 + `╗`
- Bottom border: `╚` + `═` × 68 + `╝`
- Side borders: `║` + 68 chars content + `║`

### 2. Implementation Requirements:
- **NEVER manually count spaces for centering**
- **ALWAYS use Python's `.center(68)` method** for automatic alignment
- **NEVER use complex ASCII block letters** - they are error-prone and difficult to align
- Use simple text-based designs with box-drawing characters

### 3. Correct Implementation Pattern:
```python
print("╔" + "═" * 68 + "╗")
print("║" + " " * 68 + "║")
print("║" + "──────────────────────────────".center(68) + "║")
print("║" + "BANNER TITLE TEXT".center(68) + "║")
print("║" + "Subtitle or Description".center(68) + "║")
print("║" + "──────────────────────────────".center(68) + "║")
print("║" + " " * 68 + "║")
print("╚" + "═" * 68 + "╝")
```

### 4. Verification Before Commit:
- Verify each banner line is exactly 70 characters total
- Test the banner output in the actual CLI to confirm alignment
- If borders don't align, the implementation is WRONG

### 5. Approved Banner Designs:
Current approved banners in the codebase:
- **Single Event Tournament Menu** ([MainProgramV5_2.py:194-205](MainProgramV5_2.py#L194-L205)) - "HANDICAP CALCULATION SYSTEM"
- **Multi-Event Tournament Menu** ([MainProgramV5_2.py:745-753](MainProgramV5_2.py#L745-L753)) - "TOURNAMENT CONTROL SYSTEM"

### 6. Why This Matters:
**Professionalism = Attention to Detail**

This software is being considered for use at professional woodchopping competitions (Missoula Pro-Am, Mason County Western Qualifier). Judges and event organizers will judge the system's credibility partly by its presentation. Misaligned banners signal carelessness and reduce confidence in the system's accuracy.

**This is NOT optional. Proper alignment is a requirement, not a preference.**

## ⚠️ CRITICAL DEVELOPMENT RULE - LLM PROMPT MAINTENANCE

**STANDING ORDER (MANDATORY):**

LLM prompts are CRITICAL to prediction accuracy. When system features change, prompts MUST be updated to maintain AI reasoning quality.

### 1. When to Update Prompts:
- **Adding prediction features** (tournament weighting, new baselines, etc.)
- **Changing prediction methodology** (time-decay formulas, scaling algorithms)
- **Adding system capabilities** (new statistics, confidence metrics)
- **Fixing prediction bugs** (if LLM needs to handle differently)
- **Adding optional parameters** (new contextual flags)

### 2. Which Prompts Exist:
- **Time Prediction** (`woodchopping/predictions/ai_predictor.py::predict_competitor_time_with_ai()`)
  - Purpose: Quality adjustment to baseline times
  - Critical: Tournament context, baseline sophistication, time-decay
- **Fairness Assessment** (`woodchopping/simulation/fairness.py::get_ai_assessment_of_handicaps()`)
  - Purpose: Analyze Monte Carlo results, diagnose bias patterns
  - Critical: Competitor statistics, variance analysis, consistency
- **Championship Analysis** (`woodchopping/simulation/fairness.py::get_championship_race_analysis()`)
  - Purpose: Sports commentary for championship races
  - Critical: Win probabilities, matchup analysis, upset potential

### 3. Prompt Update Checklist:
When system changes affect predictions:
- [ ] **Identify affected prompts** (which prompts reference this feature?)
- [ ] **Add system context** (explain new capability to LLM)
- [ ] **Add conditional sections** (if feature is optional)
- [ ] **Update examples** (show new behavior in action)
- [ ] **Test thoroughly** (A/B test vs old prompt if possible)
- [ ] **Update documentation**:
  - [ ] `PROMPT_CHANGELOG.md` (log version, changes, rationale)
  - [ ] `PROMPT_ENGINEERING_GUIDELINES.md` (if new patterns introduced)
  - [ ] `LLM_PROMPT_AUDIT_2026.md` (mark issues as resolved)

### 4. Example: Tournament Weighting Feature
When V4.4 added 97% tournament weighting:
```python
# ❌ BAD - LLM has no idea tournament weighting exists
prompt = f"Baseline: {baseline:.1f}s. Adjust for quality."

# ✅ GOOD - LLM understands the context
if tournament_weighted:
    prompt += f"""
⚠️ TOURNAMENT CONTEXT
Competitor already competed on THIS EXACT WOOD
Tournament result: {tournament_time:.1f}s (97% weight)
Your adjustment should be MINIMAL - wood is PROVEN
"""
```

### 5. Why This Matters:
**Prompt = LLM's Understanding**

LLM cannot infer system internals. If you add sophisticated features (tournament weighting, adaptive time-decay, convergence calibration) but don't update prompts, the LLM will:
- Apply incorrect adjustments (treating sophisticated baseline as simple average)
- Miss opportunities (not leveraging high-confidence tournament data)
- Generate worse predictions (double-adjusting for already-modeled factors)

**This is NOT optional. Prompt updates are part of the feature implementation.**

### 6. Documentation Standards:
See `PROMPT_ENGINEERING_GUIDELINES.md` for:
- Core principles (clarity, structure, context management)
- STRATHEX-specific guidelines
- Testing & validation procedures
- Versioning & change management
- Common pitfalls and how to avoid them

**This is NOT optional. Prompt maintenance is critical to prediction accuracy.**

## Architecture

### Core Components

**MainProgramV5_2.py** - Tournament management interface
- Multi-round tournament system (heats → semis → finals)
- Main menu loop with 8 main options covering tournament modes, championship simulator, personnel management, and system functions
- **Option 1**: Single Event Tournament - Design and run individual events with multi-round progression
- **Option 2**: Multi-Event Tournament - Design complete tournament days with multiple independent events
- **Option 3 (NEW V5.0)**: Championship Race Simulator - Fun predictive tool for analyzing race outcomes without handicaps
- Tournament state management (`tournament_state` dict) tracks event configuration, rounds, competitors, and handicap results
- Multi-event tournament state (`multi_event_tournament_state` dict) tracks multiple events with independent configurations
- Legacy single-heat mode preserved for backward compatibility via `heat_assignment_df`

**woodchopping/** - Modular package (V5.0 fully modular architecture)
- All business logic organized by domain: data loading, predictions, handicaps, simulation, UI
- **data/**: Excel I/O, validation, preprocessing
- **predictions/**: Baseline, ML (XGBoost), LLM (Ollama), diameter scaling, prediction aggregation
- **handicaps/**: Handicap calculation logic
- **simulation/**: Monte Carlo fairness validation with individual competitor statistics tracking (NEW V5.0)
- **ui/**: User interface modules for wood, competitors, handicaps, tournaments, personnel, multi-event tournaments, championship simulator (NEW V5.0)

**woodchopping.xlsx** - Data persistence
- `Competitor` sheet: CompetitorID, Name, Country, State/Province, Gender
- `wood` sheet: Species data with multipliers
- `Results` sheet: Historical performance data (CompetitorID, Event, Time, Species, Diameter, Quality, HeatID, Date)

### Key Architectural Patterns

**Bidirectional ID/Name Mapping**
- Competitors stored by ID in Excel, referenced by name in UI
- `get_competitor_id_name_mapping()` returns both `id_to_name` and `name_to_id` dicts
- Critical for `append_results_to_excel()` and competitor lookups

**Cascading Fallback Logic for Predictions**
- Level 1: Exact match (competitor + species + event)
- Level 2: Competitor + event (any species)
- Level 3: Event baseline (all competitors, that event)
- Implemented in `get_competitor_historical_times_flexible()` and `get_event_baseline_flexible()`

**Absolute Variance Modeling**
- All competitors get ±3 second performance variation in simulations
- Proven fairer than proportional variance (31% vs 6.7% win rate spread in testing)
- Implemented in `simulate_single_race()`

**Tournament Result Weighting (Same-Wood Optimization)**
- **CRITICAL V4.4 FEATURE**: When generating semis/finals, handicaps are AUTOMATICALLY RECALCULATED using heat/semi results
- Tournament results from completed rounds weighted at 97% vs historical data (3%)
- Rationale: Same wood across all rounds = most accurate predictor possible
- Formula: `prediction = (tournament_time × 0.97) + (historical_baseline × 0.03)`
- Automatic activation in `generate_next_round()`:
  1. Extracts actual times from completed rounds via `extract_tournament_results()`
  2. Passes tournament times to `calculate_ai_enhanced_handicaps()` via `tournament_results` parameter
  3. `get_all_predictions()` applies 97% weighting to same-tournament times
  4. Confidence upgraded to "VERY HIGH" when tournament data used
- Example: Heat result 27.1s (TODAY, same wood) beats historical 24.5s (YEARS ago, different wood)
- Eliminates previous issue where semis/finals ignored fresh performance data from earlier rounds
- See `explanation_system_functions.py` Improvement #4 for judge-facing documentation

**Tournament State Management**
```python
tournament_state = {
    'event_name': str,
    'num_stands': int,                      # Available chopping stands
    'format': str,                          # 'heats_to_finals' or 'heats_to_semis_to_finals'
    'all_competitors': list,                # Competitor names
    'all_competitors_df': DataFrame,
    'rounds': list,                         # List of round objects (heats/semis/finals)
    'capacity_info': dict,                  # From calculate_tournament_scenarios()
    'handicap_results_all': list,           # [{name, mark, predicted_time, ...}, ...]
    'wood_species': str,                    # Wood characteristics for recalculation
    'wood_diameter': float,
    'wood_quality': int,
    'event_code': str
}
```

Each round object structure:
```python
{
    'round_name': str,                     # "Heat 1", "Semi-Final A", etc.
    'round_type': str,                     # 'heat', 'semi', 'final'
    'competitors': list,                   # Competitor names in this round
    'handicap_results': list,              # Handicap data for these competitors
    'num_to_advance': int,                 # Top N advance to next round
    'status': str,                         # 'pending', 'in_progress', 'completed'
    'results': dict,                       # {competitor_name: actual_time, ...}
    'advancers': list                      # Names of competitors advancing
}
```

**Multi-Event Tournament State Management**
```python
multi_event_tournament_state = {
    'tournament_mode': 'multi_event',
    'tournament_name': str,                # Tournament name
    'tournament_date': str,                # Tournament date
    'total_events': int,                   # Number of events
    'events_completed': int,               # Number of completed events
    'current_event_index': int,            # Current event index
    'events': [                            # List of event objects
        {
            'event_id': str,               # Unique event identifier
            'event_name': str,             # "225mm SB", "300mm UH", etc.
            'event_order': int,            # Event sequence number
            'status': str,                 # 'pending', 'configured', 'ready', 'in_progress', 'completed'
            'wood_species': str,           # Wood characteristics (independent per event)
            'wood_diameter': float,
            'wood_quality': int,
            'event_code': str,
            'num_stands': int,             # Tournament configuration (independent per event)
            'format': str,
            'capacity_info': dict,
            'all_competitors': list,       # Competitors (independent per event)
            'all_competitors_df': DataFrame,
            'handicap_results_all': list,
            'rounds': list,                # Same structure as single-event system
            'final_results': {             # Top 3 placements
                'first_place': str,
                'second_place': str,
                'third_place': str,
                'all_placements': dict
            }
        }
    ]
}
```

**Key Multi-Event Design Decisions:**
- Each event is essentially a complete `tournament_state` wrapped in a list
- Tournament result weighting (97%) applies within each event only (not cross-event)
- Event-aware HeatID format: `"<event_code>-<event_name>-<round_name>"`
- Sequential workflow auto-advances to next incomplete round
- Auto-save after major operations (add event, generate schedule, record results)

**AI Integration**
- Uses Ollama API (localhost:11434) with qwen2.5:7b model
- `call_ollama(prompt, model)` handles all AI requests
- Three AI use cases:
  1. Time prediction with quality adjustments (`predict_competitor_time_with_ai()`)
  2. Fairness assessment of Monte Carlo results (`get_ai_assessment_of_handicaps()`)
  3. Championship race analysis for outcome predictions (`get_championship_race_analysis()`) - NEW V5.0
- Graceful fallback if Ollama unavailable

**Championship Simulator (NEW V5.0)**
- Standalone fun predictive tool accessible via Main Menu Option 3
- Simulates championship-format races where all competitors start together (Mark 3)
- Workflow: wood config → event selection → competitor selection → 2M Monte Carlo simulations → AI race analysis
- Features:
  - Reuses existing prediction engine (baseline, ML, LLM)
  - Runs 2 million simulations for high statistical confidence
  - Tracks individual competitor statistics (mean, std_dev, percentiles, consistency rating)
  - AI-powered race analysis focusing on matchups, favorites, dark horses, and competitive dynamics
  - View-only (no tournament state changes or Excel writes)
- Key difference from handicap mode: Predicts win probabilities for equal-start races instead of testing handicap fairness
- Implementation: `woodchopping/ui/championship_simulator.py`, `woodchopping/simulation/fairness.py::get_championship_race_analysis()`

**Monte Carlo Enhanced Statistics (NEW V5.0)**
- `run_monte_carlo_simulation()` now tracks per-competitor finish time statistics across all simulations
- New return fields in analysis dict:
  - `competitor_time_stats`: Dict mapping competitor name to statistics:
    - `mean`: Average finish time across all simulations
    - `std_dev`: Standard deviation (validates ±3s variance model)
    - `min`/`max`: Range of finish times observed
    - `p25`/`p50`/`p75`: Percentile distribution
    - `consistency_rating`: "Very High"/"High"/"Moderate"/"Low" based on std_dev
- Consistency rating thresholds:
  - Very High: std_dev ≤ 2.5s (very predictable performance)
  - High: std_dev ≤ 3.0s (expected variance, matches ±3s model)
  - Moderate: std_dev ≤ 3.5s (slightly above expected)
  - Low: std_dev > 3.5s (high variability, unpredictable)
- Memory overhead: ~64 MB for 4 competitors @ 2M simulations, ~160 MB for 10 competitors
- Used by championship simulator to show individual competitor performance analysis

**Championship Events vs Handicap Events (Multi-Event Tournaments)**

The system supports two event types in multi-event tournaments:

**Handicap Events** (default):
- System calculates individual marks based on AI-predicted performance
- Uses historical data + AI predictions to create fair competition
- All competitors should theoretically finish simultaneously
- Back markers (slower) start first with lower marks, front markers (faster) start last with higher marks
- Monte Carlo simulation validates fairness (target: <2% win rate spread)
- Full analysis and manual adjustment workflow available

**Championship Events**:
- All competitors receive Mark 3 (same start time)
- Fastest raw time wins - traditional "race to the finish" format
- No AI predictions or handicap calculations needed
- Event type selected during event configuration (Option 2)
- Championship events skip handicap calculation (Option 5)
- Championship events bypass Monte Carlo analysis (Option 6 simplified)
- Approval is simplified - no manual adjustments (Option 7)
- Tournament result weighting does NOT apply (all marks stay Mark 3 in semis/finals)

**Multi-Event Tournament Workflow**:
- Tournaments can mix Handicap and Championship events
- Each event has independent configuration (wood, competitors, format, event type)
- Championship events auto-generate Mark 3 during configuration and set status='ready'
- Handicap events require batch calculation (Option 5) to generate marks
- Both event types flow through same round generation and results entry workflow
- Results from both event types append to Excel Results sheet

**Event Type Field**:
- Stored in event state as `event_type: 'handicap' | 'championship'`
- Default is 'handicap' for backward compatibility
- Legacy tournaments loaded without event_type default to 'handicap'

## Development Workflow

### Typical Judge Workflow
1. Configure wood characteristics (species, diameter, quality)
2. Configure tournament (stands, format, event name)
3. Select all competitors from master roster
4. Calculate handicaps for all competitors
5. View handicaps + optional Monte Carlo fairness analysis
6. Generate initial heats with balanced skill distribution
7. Record heat results and select advancers (repeat for all heats)
8. Generate next round (semis/finals)
9. Repeat steps 7-8 until tournament complete

### Adding New Functionality

When adding features to the modular woodchopping package:
- Follow existing naming conventions (snake_case functions)
- Place functions in appropriate modules based on domain (data/, predictions/, handicaps/, simulation/, ui/)
- Excel operations should use openpyxl, not pandas to_excel (for atomic appends)
- All UI functions should return updated state objects (e.g., `wood_selection` dict, DataFrames)
- Use `format_wood(wood_selection)` to display current wood config in menus
- Export new functions through module `__init__.py` files for easy importing

### Monte Carlo Simulation

Default: 250,000 race iterations per simulation
- `run_monte_carlo_simulation()` returns analysis dict with win rates, finish positions, spreads
- `visualize_simulation_results()` creates text-based bar charts
- `get_ai_assessment_of_handicaps()` rates fairness: Excellent/Very Good/Good/Fair/Poor/Unacceptable
- Fairness threshold: win rate spread < 2% = Excellent

### AAA Competition Rules Compliance

Hard constraints enforced in code:
- 3-second minimum mark
- 180-second maximum time limit
- Marks rounded up to whole seconds
- Slowest predicted time gets Mark 3 (front marker)
- Fastest predicted time gets highest mark (back marker)

## Data Model

**Competitor Entry Requirements:**
- Minimum 3 historical times required for new competitors
- Each time requires: Event (SB/UH), Time (seconds), Species, Diameter (mm), Quality (0-10), optional Date

**Wood Quality Scale:**
- 0-3: Soft/rotten wood (faster times)
- 4-7: Average firmness for species
- 8-10: Above average firmness (slower times)

**Event Codes:**
- SB: Standing Block
- UH: Underhand
- (Future: 3-Board Jigger planned but not yet implemented)

## Known Future Enhancements

See [NewFeatures.md](NewFeatures.md) for V3 roadmap:
- Upgrade to qwen2.5:37b model
- Re-add manual formula calculations for comparison vs AI
- Tournament persistence (save/load state) - partially implemented
- Time-weighted historical data (weight recent performances more heavily)
- 3-Board Jigger event support (blocked by limited training data)

## Important Context

**Why Absolute Variance:**
Testing revealed proportional variance (e.g., ±5% of predicted time) creates biased results. A 30-second chopper with ±5% = ±1.5s range, while a 60-second chopper gets ±3s range. This gives faster choppers unfair advantage. Absolute ±3s variance proved fair across all skill levels because real-world consistency factors (technique, wood grain, equipment) affect everyone equally.

**Handicap Mark Convention:**
Lower marks = front markers (better competitors, start earlier)
Higher marks = back markers (slower competitors, start later with delay)
All competitors should theoretically finish simultaneously in perfect system.

**Project Origin:**
Academic project for woodchopping competition management. Currently being considered for use at Missoula Pro-Am and Mason County Western Qualifier. Tested against Australian handicapping data (150+ years institutional knowledge).

## Documented Solutions

`docs/solutions/` — documented solutions to past problems (bugs, best practices, workflow improvements), organized by category with YAML frontmatter (`module`, `tags`, `problem_type`). Relevant when implementing or debugging in documented areas.
