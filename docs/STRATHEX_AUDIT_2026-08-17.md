# STRATHEX V6 Maintenance Audit

**Audit date:** 2026-08-17  
**Audited repository:** `SquirmyWormy275/STRATHEX`  
**Audited base commit:** `db8cf74c175feab57a015e67813e5a72b207b5e4`  
**Pinned engine:** STRATHMARK `47bb143` / package version `0.4.1`  
**Repair branch:** `agent/repair-strathmark-integration`

## Objective

Audit the original STRATHEX program, identify defects and integration drift, and
repair the existing implementation without adding features or changing the
project's intended tournament workflow, mark arithmetic, judge-facing format,
plain-text operating style, prompts, or event semantics.

## Scope and source hierarchy

The documentation review was completed before code changes. The audit covered:

- current root documentation and system-status reports;
- current architecture, project-structure, ML-audit, prompt, interpolation, and
  handicap documentation;
- all records under `docs/solutions/`;
- archived V2-V5 implementation, validation, ML redesign, and prompt reports;
- all version-controlled wiki pages;
- the full in-program `explanation_system_functions.py` help system;
- the bundled August 2024 AAA rules text and QAA rules text;
- current source, test, CI, packaging, workbook I/O, tournament, prediction,
  simulation, and adapter paths;
- the exact STRATHMARK commit pinned by `pyproject.toml`.

Where documents disagreed, the current V6 architecture decisions and the
pinned engine's executable API were treated as authoritative. Historical
documents were used to recover intent, not to reintroduce superseded behavior.

## Preserved invariants

This repair does not change the following:

- STRATHEX remains the tournament application and STRATHMARK remains the
  handicap engine.
- Existing single-event, multi-event, bracket, championship, results-entry,
  save/resume, and menu flows are unchanged.
- Existing function signatures used by the UI are unchanged.
- Marks are still assigned by the pinned STRATHMARK calculator.
- The existing Mark 3 floor, mark ceiling, gap rounding, sorting, and
  per-competitor variance behavior are unchanged.
- QAA lookup tables are not restored as time-prediction scaling data.
- Wood quality remains `1 = softest`, `5 = average`, `10 = hardest`.
- No prompt wording, tournament format, database schema, or workbook data is
  changed.
- No dependency pin is advanced to the newer STRATHMARK redesign.

## Executive findings

| Severity | Finding | Status in this repair |
|---|---|---|
| Critical | Historical data was passed into the wrapper but discarded when `HandicapCalculator()` was created, so STRATHMARK never trained an ML model for live marks. | Fixed |
| Critical | The comparison table called `get_all_predictions()` without `ml_model` or `results_df`, making the ML column unavailable even when sufficient data existed. | Fixed |
| High | V6 documentation specifies expected-error method selection, but live marks used STRATHMARK's older fixed cascade. A working LLM could therefore prevent ML from ever being selected. | Fixed at the adapter boundary |
| High | Predictions were run a second time after marks were assigned. The values displayed to the judge could differ from the values used to calculate marks, and LLM work was duplicated. | Fixed |
| High | STRATHEX documents 97% same-tournament weighting, but the adapter left STRATHMARK's completed-round count at one, which applies 65%. | Fixed |
| High | Roster gender was never joined onto Results or passed into `CompetitorRecord`; STRATHMARK encoded every missing value as female for a live ML feature. | Fixed |
| High | The comparison adapter supplied `/api/generate` to a function that appends `/api/generate`, producing a duplicated Ollama endpoint for non-neutral wood quality. | Fixed |
| High | Comprehensive analysis imported `format_ai_assessment`, but the function did not exist. The resulting internal import failure was reported to users as an Ollama problem. | Fixed |
| Medium | Simulation and fairness wrappers imported STRATHMARK directly, and simulation reached into a private variance helper, contradicting the documented single-adapter boundary. | Consolidated behind the adapter |
| Medium | ML was retrained for every event even when historical and wood data had not changed. | Fixed with content-fingerprinted, one-dataset cache |
| Medium | Most historical prediction “tests” are executable reports excluded from pytest, so CI did not verify that ML trained, appeared, or could be selected. | Fixed with collected regression tests |
| High | One Excel append recovery path can replace a damaged/unreadable workbook with a Results-only workbook, bypassing the full-schema guard. | Confirmed; intentionally deferred |
| Medium | Wiki and in-app help text mix V4/V5/V6 behavior, reverse the quality scale in places, describe removed QAA scaling, and disagree on method selection and rounding. | Confirmed; intentionally deferred |
| Medium | A large retained V5 prediction stack and its dependencies remain in STRATHEX despite the V6 extraction. | Confirmed; removal deferred |
| Low | `MainProgramV5_2.py` still imports `ResultStore` directly rather than through the adapter. | Confirmed; deferred to avoid rewriting the main UI file in this focused patch |

## Root-cause analysis

### 1. ML activation failure

The current wrapper standardized the supplied historical DataFrame and built
typed competitor histories, but then instantiated:

```python
calc = HandicapCalculator()
```

The pinned STRATHMARK calculator performs lazy ML training only when
`results_df` is supplied to its constructor. The wrapper therefore guaranteed
that `_ml_model` remained `None`.

The subsequent display conversion independently called
`get_all_predictions()` without an `ml_model`, `results_df`, or wood-property
DataFrame. This made the visible ML result unavailable as well.

### 2. Selection-policy mismatch

The current V6 STRATHEX architecture describes comparison of Baseline, ML, and
LLM results followed by expected-error selection. The pinned STRATHMARK package
contains that selector, but its `HandicapCalculator.calculate()` still uses the
older fixed cascade.

The repaired adapter now:

1. trains or reuses the pinned STRATHMARK `MLModel`;
2. runs all methods once per competitor;
3. calls STRATHMARK's own `select_best_prediction()`;
4. passes the selected time back through STRATHMARK's calculator using its
   existing manual-value bridge;
5. replaces the bridge metadata with the actual selected method, confidence,
   explanation, and exact comparison objects.

This keeps prediction selection consistent with V6 intent while leaving all
mark arithmetic inside STRATHMARK.

### 3. Same-tournament weighting mismatch

STRATHEX passes a single latest same-tournament time and explicitly describes a
97%/3% blend. STRATHMARK's pinned data type uses a graduated policy:

- one completed round: 65%;
- two: 80%;
- three: 90%;
- four or more: 97%.

The adapter previously set the time but not the round count. It now maps the
existing STRATHEX policy to `num_tournament_rounds=4` whenever a valid
same-tournament time is present. No tournament workflow or stored state changes.

### 4. Gender feature loss

Gender resides in the Competitor sheet, while model-training rows come from the
Results sheet. The extraction never joined those sources. The pinned model's
feature engineering treats any value other than `M` as zero/female, so missing
metadata was not neutral.

The wrapper now silently loads roster metadata, fills only missing/invalid
gender values in a copy of the historical DataFrame, and supplies normalized
`M`/`F` values to live `CompetitorRecord` objects. Existing result values and
input DataFrames are not mutated.

### 5. Duplicate prediction execution

The old adapter calculated marks and then reran all methods for display. Besides
doubling LLM calls, this could expose different outputs when an LLM response,
timeout, or model state changed between passes.

The repaired adapter retains the exact `PredictionResult` objects used for
selection and converts those same objects for the existing three-column display.

### 6. Broken comprehensive-analysis formatter

The existing analysis screen imports `format_ai_assessment` from the fairness
wrapper. That symbol was absent from both STRATHEX and the pinned STRATHMARK
package. The broad caller exception then mislabeled the problem as an Ollama
timeout.

A small plain-text wrapping function has been restored under the already
expected name. It preserves headings, paragraph order, wording, and the
terminal-oriented presentation.

## Optimization changes

The repair includes only optimizations that remove redundant work without
altering outputs:

- one prediction pass per competitor instead of two;
- one ML training operation per unchanged historical/wood dataset;
- model-cache invalidation based on DataFrame content, columns, dtypes, and
  shape, so newly loaded results retrain automatically;
- one centralized engine boundary for calculation, fairness, persistence
  construction, and Monte Carlo delegation;
- direct reuse of STRATHMARK's calculated `std_dev` rather than a second
  variance estimate for the display/simulation dictionary.

## Regression coverage added

`tests/test_strathmark_integration.py` verifies that:

1. roster gender enrichment is non-mutating and normalizes accepted values;
2. gender reaches `CompetitorRecord`;
3. the existing STRATHEX 97% same-tournament policy reaches STRATHMARK;
4. ML training receives the historical and wood DataFrames;
5. the trained ML object reaches every comparison call;
6. expected-error selection can choose ML;
7. displayed predictions are reused rather than recomputed;
8. the Ollama client receives the base URL, not a duplicated endpoint;
9. selected method metadata survives STRATHMARK mark assignment;
10. STRATHMARK's variance result reaches the existing simulation dictionary;
11. the comprehensive-analysis formatter exists and preserves terminal width.

The existing NaT-boundary and workbook-guard tests remain unchanged.

## Confirmed issues intentionally not changed in this patch

### Destructive workbook fallback

`append_results_to_excel()` has a broad exception path that creates a new
workbook and saves it at the production path. Unlike `ensure_workbook()`, that
fallback can create only the Results sheet and overwrite a workbook that failed
to load for reasons other than nonexistence.

This is a data-integrity issue, but it should be repaired with isolated
corruption/permission tests and a transactional write strategy. Mixing that
large I/O change into the engine-integration repair would increase the chance of
damaging competition data.

### Documentation and in-program help drift

The wiki and help wizard need a dedicated reconciliation pass. Current
contradictions include:

- expected-error selection versus fixed priority;
- 23/27-feature ML descriptions versus older six-feature descriptions;
- correct and reversed quality-scale definitions;
- active versus removed QAA time scaling;
- nearest, ceiling, and standard rounding statements;
- stale module names and version labels;
- inconsistent Results schema examples;
- Unicode-heavy screens despite the ASCII field-terminal decision.

The current runtime repair does not rewrite judge-facing guidance piecemeal,
because partial edits would leave a different set of contradictions.

### Retained V5 implementation stack

Large local Baseline/ML/LLM modules and corresponding heavy dependencies remain
in the package even though V6 delegates the live engine to STRATHMARK. Some are
still used as presentation or compatibility layers. Removal requires an
import-graph and packaging-only change set with full installation tests.

### Main-program direct store import

The main entry point still constructs `ResultStore` directly. An adapter factory
now exists, but replacing the import in the large main program is deferred to a
small follow-up once this focused calculation patch is validated. Runtime
behavior is not currently wrong; the issue is architectural containment.

## Dependency decision

The STRATHMARK commit remains pinned to `47bb143`. The current STRATHMARK main
branch contains a broader prediction-engine redesign. Advancing the pin during
a maintenance audit would change model behavior and violate the instruction to
preserve project intent. The pin should move only through a separately measured
migration with prediction-diff, mark-diff, and tournament replay reports.

## Operational validation checklist

Before merge, validate on both CI platforms and one real workbook copy:

- `ruff check .`
- `ruff format --check .`
- `pytest tests/ -m "not ollama"`
- package build and clean-environment install
- import smoke test
- one SB and one UH handicap sheet with Ollama unavailable
- one non-quality-5 sheet with Ollama available
- confirm the ML column contains values when training requirements are met
- confirm at least one controlled fixture allows ML selection
- confirm displayed selected values equal the values used for marks
- confirm a later-round competitor reports tournament weighting
- run Monte Carlo and comprehensive analysis
- enter results only against a disposable workbook copy

## Conclusion

The principal V6 integration was present structurally but not functionally:
historical data crossed the adapter, while the trained ML model did not. The
repair restores the documented three-method comparison and expected-error
selection, corrects same-tournament and roster metadata transfer, removes
duplicate prediction work, and leaves the tournament application and mark
calculation semantics intact.
