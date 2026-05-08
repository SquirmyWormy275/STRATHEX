# STRATHEX Prompt Engineering Guidelines

**Document Purpose**: Establish best practices for creating, maintaining, and optimizing LLM prompts in the STRATHEX Woodchopping Handicap System
**Date Created**: January 12, 2026
**Last Updated**: January 12, 2026
**Version**: 1.0

---

## Table of Contents

1. [Core Principles](#core-principles)
2. [STRATHEX-Specific Guidelines](#strathex-specific-guidelines)
3. [Prompt Structure Standards](#prompt-structure-standards)
4. [Context Management](#context-management)
5. [Versioning & Change Management](#versioning--change-management)
6. [Testing & Validation](#testing--validation)
7. [Documentation Requirements](#documentation-requirements)
8. [Common Pitfalls](#common-pitfalls)
9. [Example Improvements](#example-improvements)
10. [Maintenance Checklist](#maintenance-checklist)

---

## Core Principles

### 1. **Clarity Over Brevity**
- **Principle**: Prioritize clear communication over token conservation
- **Rationale**: Input tokens are cheap; poor predictions from vague prompts are expensive
- **Example**:
  ```
  ❌ BAD:  "Adjust baseline for quality"
  ✅ GOOD: "Apply wood quality adjustment to baseline time. Quality >5 = harder = slower.
           Use ±2% per quality point deviation from baseline (quality 5)."
  ```

### 2. **Structured Information Hierarchy**
- **Principle**: Organize prompts with clear sections and headers
- **Rationale**: Helps LLM parse and prioritize information
- **Example**:
  ```
  ✅ GOOD STRUCTURE:
  HANDICAPPING OBJECTIVE
  <high-level goals>

  COMPETITOR PROFILE
  <specific data>

  BASELINE INTERPRETATION
  <what the baseline means>

  YOUR TASK
  <what to do with this information>
  ```

### 3. **Explicit Instructions**
- **Principle**: Never assume the LLM "knows" what to do
- **Rationale**: Models follow instructions, not intuition
- **Example**:
  ```
  ❌ BAD:  "Here's the quality rating: 8"
  ✅ GOOD: "Quality Rating: 8/10
           - HIGHER number = HARDER wood = SLOWER cutting = HIGHER time
           - Apply +6% to baseline (8-5=3 points, 3×2%=6%)"
  ```

### 4. **Context is King**
- **Principle**: Provide system context that LLM can't infer
- **Rationale**: LLM doesn't know about your V4.4 features or internal calculations
- **Example**:
  ```
  ❌ BAD:  "Baseline: 27.0s from tournament"
  ✅ GOOD: "⚠️ TOURNAMENT CONTEXT
           Competitor already competed on THIS EXACT WOOD
           Tournament result: 27.1s (97% weight)
           Historical avg: 24.5s (3% weight)
           Your adjustment should be MINIMAL - wood is PROVEN"
  ```

### 5. **Constrain the Output**
- **Principle**: Specify exact output format and range
- **Rationale**: Prevents parsing errors and unexpected responses
- **Example**:
  ```
  ✅ GOOD:
  RESPONSE REQUIREMENT
  Return in EXACT format: <multiplier> | <confidence> | <explanation>
  - multiplier: decimal 0.85-1.15 (e.g., 1.07)
  - confidence: HIGH, MEDIUM, or LOW only
  - explanation: ONE sentence, max 15 words
  ```

---

## STRATHEX-Specific Guidelines

### 1. **Always Communicate System Intelligence**

**Rule**: When baseline/predictions use sophisticated models, explain that to the LLM

**Why**: Prevents "double-adjustment" where LLM tries to fix things already modeled

**Implementation**:
```python
# ❌ BAD - LLM doesn't know what went into baseline
prompt = f"Baseline: {baseline:.1f}s. Adjust for quality {quality}."

# ✅ GOOD - LLM knows baseline sophistication
prompt = f"""
Baseline: {baseline:.1f}s

BASELINE V2 MODEL ALREADY INCLUDES:
✓ Time-decay weighting (recent results emphasized)
✓ Event type effects (SB vs UH)
✓ Diameter curve (polynomial log-space)
✓ Wood hardness (learned from 6 properties)
✓ Competitor-specific random effects

YOUR ADJUSTMENT SCOPE:
✗ DO NOT adjust for species hardness (already modeled)
✓ DO adjust for wood QUALITY (condition within species)
"""
```

### 2. **Tournament Result Weighting Context**

**Rule**: When tournament_results parameter is passed, ALWAYS add tournament context section

**Why**: Your V4.4 killer feature - LLM must understand 97% same-wood weighting

**Implementation**:
```python
if tournament_results and competitor_name in tournament_results:
    tournament_time = tournament_results[competitor_name]
    prompt += f"""
⚠️ TOURNAMENT CONTEXT - CRITICAL INFORMATION ⚠️

This competitor has ALREADY COMPETED on THIS EXACT WOOD.
Tournament result: {tournament_time:.1f}s (same block, recent)

IMPORTANCE:
- Same wood across rounds = MOST ACCURATE predictor
- Tournament time from TODAY beats historical from YEARS AGO
- System applies 97% weight to tournament time

YOUR TASK:
- Apply MINIMAL quality adjustment (±1-3% max)
- Do NOT apply standard adjustments - wood is PROVEN
"""
```

### 3. **Adaptive Time-Decay Explanation**

**Rule**: Explain why baseline might differ from simple historical average

**Why**: System uses adaptive half-lives (365/730/1095 days) - LLM should know

**Implementation**:
```python
prompt += f"""
TIME-DECAY WEIGHTING (HOW BASELINE WAS CALCULATED):
- Active competitors: 365-day half-life (emphasize recent form)
- Moderate competitors: 730-day half-life (2-year balance)
- Inactive competitors: 1095-day half-life (preserve old data)

For {competitor_name}: {activity_level}, {half_life_days}-day half-life used

This means recent performances weighted MUCH higher than historical peaks.
For aging competitors, baseline reflects CURRENT ability, not peak from years ago.
"""
```

### 4. **QAA Validation Context**

**Rule**: Explain empirical validation source for species adjustments

**Why**: Establishes authority of data, clarifies LLM's distinct role

**Implementation**:
```python
prompt += """
WOOD CHARACTERISTICS DATABASE (QAA VALIDATED):

Species adjustments derived from Queensland Axemen's Association (QAA)
empirical handicapping manual - 150+ YEARS of competition data.
These are PROVEN, not theoretical estimates.

{species_list}

Your quality adjustment modifies CONDITION within species (soft/hard variation),
NOT the species baseline (already empirically validated).
"""
```

### 5. **Individual Competitor Statistics (V5.0 Feature)**

**Rule**: Include per-competitor variance analysis in fairness assessments

**Why**: V5.0 added this capability - valuable diagnostic data not being used

**Implementation**:
```python
if 'competitor_time_stats' in analysis:
    stats_section = "\n\nPER-COMPETITOR STATISTICS:\n"
    for name, stats in analysis['competitor_time_stats'].items():
        stats_section += f"  - {name}: mean={stats['mean']:.1f}s, "
        stats_section += f"std_dev={stats['std_dev']:.2f}s, "
        stats_section += f"consistency={stats['consistency_rating']}\n"

    stats_section += """
CONSISTENCY ANALYSIS REQUIRED:
- Are there competitors with std_dev > 3.5s? (high variance)
- Does high variance correlate with LOW confidence predictions?
- Does ±3s model assumption hold for all competitors?
"""
    prompt += stats_section
```

---

## Prompt Structure Standards

### Standard Template Structure

All STRATHEX prompts should follow this hierarchy:

```
1. ROLE DEFINITION
   "You are a [specific role] [specific task]..."

2. HIGH-LEVEL OBJECTIVE
   Why this task matters, what success looks like

3. CONTEXT SECTIONS (order by importance)
   - Critical context (tournament results, special conditions)
   - Competitor profile
   - System capabilities (what's already modeled)
   - Input data (wood specs, historical data)
   - Methodology explanation

4. INTERPRETATION GUIDANCE
   - What the inputs mean
   - How to use the provided data
   - What NOT to do (common mistakes)

5. ANALYSIS REQUIREMENTS
   - Step-by-step reasoning expected
   - Specific questions to answer
   - Edge cases to consider

6. OUTPUT FORMAT
   - Exact structure required
   - Allowed values/ranges
   - Examples of correct responses
```

### Section Header Standards

**Use clear, ALL CAPS headers for major sections:**
```
✅ GOOD:
HANDICAPPING OBJECTIVE
COMPETITOR PROFILE
BASELINE INTERPRETATION

❌ BAD:
About the Competitor
What we need from you
Some context
```

**Use indented subsections for nested content:**
```
✅ GOOD:
QUALITY RATING SYSTEM

10 = Extremely hard
   - Maximum difficulty
   - MULTIPLY baseline by 1.12-1.15
   - Example: 40s → 45-46s

9 = Very hard
   - Major difficulty, knots
   - MULTIPLY baseline by 1.08-1.12
```

---

## Context Management

### Critical vs Background Context

**Critical Context** (Must be prominently placed, repeated if necessary):
- Tournament result weighting flags
- Special conditions (championship vs handicap mode)
- System limitations (low confidence warnings)
- Required output format

**Background Context** (Can be placed lower, less emphasis):
- General handicapping principles
- Historical system evolution
- Statistical methodology details

### Dynamic Context Sections

Use conditional sections for optional context:

```python
# ✅ GOOD - Clear conditional inclusion
tournament_section = ""
if tournament_weighted:
    tournament_section = """
⚠️ TOURNAMENT CONTEXT
[...tournament details...]
"""

prompt = f"""
[...main prompt...]
{tournament_section}  # Conditionally inserted
[...rest of prompt...]
"""
```

```python
# ❌ BAD - Unclear/misleading
prompt = f"""
Tournament result: {tournament_time if tournament_time else "N/A"}
"""
# Problem: LLM sees "N/A" and doesn't know what that means
```

### Token Budget Management

**Input Tokens**: Be generous - clarity matters
**Output Tokens**: Be restrictive - prevent rambling

```python
# Time Prediction (fast, focused)
TOKENS_TIME_PREDICTION = 50-150  # Single number + brief explanation

# Fairness Assessment (comprehensive analysis)
TOKENS_FAIRNESS_ASSESSMENT = 3000-5000  # Multi-paragraph analysis

# Championship Commentary (narrative)
TOKENS_CHAMPIONSHIP_ANALYSIS = 800-1200  # Sports-style commentary
```

**Guideline**: Increase input context to IMPROVE output; increase output tokens to ALLOW complexity

---

## Versioning & Change Management

### Prompt Versioning System

**Directory Structure**:
```
woodchopping/
├── prompts/
│   ├── time_prediction_v1.txt
│   ├── time_prediction_v2.txt  ← Current
│   ├── fairness_assessment_v1.txt
│   ├── fairness_assessment_v2.txt  ← Current
│   ├── championship_analysis_v1.txt  ← Current
│   └── PROMPT_CHANGELOG.md
```

**Loader Function**:
```python
def load_prompt_template(prompt_name: str, version: int = None) -> str:
    """
    Load a versioned prompt template.

    Args:
        prompt_name: 'time_prediction', 'fairness_assessment', 'championship_analysis'
        version: Specific version number, or None for latest

    Returns:
        Prompt template string
    """
    if version is None:
        version = get_latest_version(prompt_name)

    path = f"woodchopping/prompts/{prompt_name}_v{version}.txt"
    with open(path, 'r') as f:
        return f.read()
```

### Change Documentation (PROMPT_CHANGELOG.md)

**Format**:
```markdown
# Prompt Changelog

## time_prediction v2 (2026-01-12)
**Changes**:
- Added tournament result weighting context section
- Added adaptive time-decay explanation
- Added Baseline V2 architecture context

**Why**:
- V4.4 tournament weighting not being communicated to LLM
- LLM treating baseline as simple average (it's sophisticated regression)
- Prevents double-adjustment for factors already modeled

**Impact**:
- Semis/finals predictions improved by 15% (less deviation from actual)
- Fewer manual adjustments needed by judges
- Better quality adjustment decisions (±1-3% vs ±5-8% previously)

**Testing**:
- A/B tested on 10 tournament scenarios
- Prediction MAE decreased from 3.2s to 2.7s
- User satisfaction: 9/10 judges approved improvements

**Rolled Back**: No
```

### Git Workflow for Prompt Changes

```bash
# 1. Create feature branch
git checkout -b prompt/time-prediction-v2

# 2. Make changes to prompt
# Edit woodchopping/predictions/ai_predictor.py

# 3. Extract prompt to versioned file (optional, recommended)
# Create woodchopping/prompts/time_prediction_v2.txt

# 4. Update PROMPT_CHANGELOG.md
# Document what changed and why

# 5. Commit with descriptive message
git commit -m "Prompt: Add tournament context to time prediction (v2)

- Added tournament result weighting explanation
- Added Baseline V2 architecture context
- Expected to improve semis/finals predictions
- See PROMPT_CHANGELOG.md for details"

# 6. Test before merging
# Run test suite with new prompt

# 7. Merge if tests pass
git checkout main
git merge prompt/time-prediction-v2
```

---

## Testing & Validation

### A/B Testing Methodology

**Phase 1: Baseline Capture**
```python
def capture_baseline_outputs(test_cases, prompt_version=1):
    """
    Run test cases with current prompt, save outputs.

    Args:
        test_cases: List of test scenarios
        prompt_version: Current prompt version

    Returns:
        Dict mapping test_id to output
    """
    results = {}
    for test_id, test_case in enumerate(test_cases):
        output = run_prediction(test_case, prompt_version)
        results[test_id] = {
            'input': test_case,
            'output': output,
            'timestamp': datetime.now()
        }

    # Save to file for comparison
    save_results(f"baseline_v{prompt_version}.json", results)
    return results
```

**Phase 2: New Prompt Testing**
```python
def compare_prompt_versions(test_cases, old_version, new_version):
    """
    Compare outputs from two prompt versions.

    Returns:
        Comparison report with metrics
    """
    old_results = load_results(f"baseline_v{old_version}.json")
    new_results = capture_baseline_outputs(test_cases, new_version)

    comparison = {
        'accuracy_improvement': calculate_accuracy(new_results) - calculate_accuracy(old_results),
        'consistency_improvement': calculate_consistency(new_results) - calculate_consistency(old_results),
        'parse_failures': count_parse_failures(new_results),
        'outliers': identify_outliers(new_results, old_results)
    }

    return generate_comparison_report(comparison)
```

### Test Case Suite

**Maintain diverse test scenarios:**

```python
TEST_CASES = [
    # Scenario 1: Standard prediction (no tournament data)
    {
        'name': 'Standard prediction',
        'competitor': 'John Smith',
        'baseline': 45.0,
        'quality': 5,
        'tournament_results': None,
        'expected_multiplier_range': (0.98, 1.02)
    },

    # Scenario 2: Tournament weighted prediction
    {
        'name': 'Tournament weighted',
        'competitor': 'Jane Doe',
        'baseline': 27.0,  # 97% of 27.1s tournament result
        'quality': 5,
        'tournament_results': {'Jane Doe': 27.1},
        'expected_multiplier_range': (0.99, 1.01),  # Should be minimal
        'expected_confidence': 'VERY HIGH'
    },

    # Scenario 3: Hard wood quality
    {
        'name': 'Hard wood (quality 8)',
        'competitor': 'Bob Jones',
        'baseline': 40.0,
        'quality': 8,
        'tournament_results': None,
        'expected_multiplier_range': (1.05, 1.08),
        'expected_time_range': (42.0, 43.2)
    },

    # Scenario 4: Soft wood quality
    {
        'name': 'Soft wood (quality 3)',
        'competitor': 'Alice Brown',
        'baseline': 50.0,
        'quality': 3,
        'tournament_results': None,
        'expected_multiplier_range': (0.95, 0.97),
        'expected_time_range': (47.5, 48.5)
    },

    # Scenario 5: Extreme quality with tournament data (edge case)
    {
        'name': 'Extreme quality + tournament',
        'competitor': 'Charlie Davis',
        'baseline': 35.0,
        'quality': 9,
        'tournament_results': {'Charlie Davis': 35.3},
        'expected_multiplier_range': (1.00, 1.03),  # Minimal despite quality 9
        'note': 'Tournament result should dominate, LLM should apply minimal adjustment'
    },

    # Scenario 6: Low confidence baseline
    {
        'name': 'Low confidence data',
        'competitor': 'Eve Wilson',
        'baseline': 60.0,
        'confidence': 'LOW',
        'quality': 5,
        'tournament_results': None,
        'expected_confidence': 'LOW or MEDIUM',
        'note': 'LLM should inherit low confidence'
    },
]
```

### Validation Metrics

**Quantitative Metrics**:
- **Prediction MAE**: Mean absolute error vs actual results (if available)
- **Consistency**: Variance across similar test cases
- **Parse Success Rate**: % of responses that parse correctly
- **Confidence Calibration**: Do "VERY HIGH" predictions actually perform better?

**Qualitative Metrics**:
- **Reasoning Quality**: Does explanation make sense?
- **Context Awareness**: Did LLM notice tournament weighting?
- **Instruction Following**: Did LLM apply minimal adjustment when asked?
- **User Satisfaction**: Judge feedback on prediction quality

---

## Documentation Requirements

### Mandatory Documentation Sync

**STANDING ORDER**: When prompts change, update these files immediately:

1. **This File** (`PROMPT_ENGINEERING_GUIDELINES.md`)
   - Update examples if patterns change
   - Add new principles learned
   - Document new prompt types

2. **PROMPT_CHANGELOG.md**
   - Log all changes with version numbers
   - Explain WHY changes were made
   - Document impact and testing results

3. **explanation_system_functions.py** (Judge-facing docs)
   - Update if prediction methodology changes
   - Explain new features in user-friendly terms
   - Add examples showing new behavior

4. **SYSTEM_STATUS.md**
   - Update "Recent Improvements" section
   - Note prompt version in system capabilities
   - Document any performance improvements

### Inline Prompt Documentation

**Always include comments explaining prompt structure:**

```python
# ✅ GOOD - Clear documentation
# Step 3: AI calibration prompt (returns multiplier)
# Build tournament context section if applicable
tournament_context_section = ""
if tournament_weighted and tournament_time:
    # CRITICAL V4.4 FEATURE: Tournament results from same wood beat historical data
    tournament_context_section = f"""
⚠️ TOURNAMENT CONTEXT - CRITICAL INFORMATION ⚠️
[...prompt content...]
"""

prompt = f"""
[...main prompt...]
{tournament_context_section}  # Conditionally inserted for tournament-weighted predictions
[...rest of prompt...]
"""
```

```python
# ❌ BAD - No documentation
section = ""
if tw and tt:
    section = f"""..."""
prompt = f"""...{section}..."""
```

---

## Common Pitfalls

### Pitfall 1: Implicit Context

**Problem**: Assuming LLM knows about system internals

```python
# ❌ BAD
prompt = f"Baseline: {baseline:.1f}s. Quality: {quality}."
# LLM doesn't know baseline includes time-decay, shrinkage, etc.
```

```python
# ✅ GOOD
prompt = f"""
Baseline: {baseline:.1f}s

BASELINE CALCULATION:
- Time-decay weighted historical average
- Shrinkage toward event baseline
- Already accounts for competitor skill and typical conditions

YOUR TASK: Adjust ONLY for wood quality (condition variation)
"""
```

### Pitfall 2: Ambiguous Output Format

**Problem**: LLM returns unparseable responses

```python
# ❌ BAD
prompt = "Predict the time and explain why."
# Response might be: "I think around 45 seconds because the wood is hard"
# How do you parse "around 45"?
```

```python
# ✅ GOOD
prompt = """
RESPONSE REQUIREMENT

Return in EXACT format: <multiplier> | <confidence> | <explanation>

Examples:
1.07 | HIGH | Quality 8 wood increases resistance by 7%
0.95 | HIGH | Quality 3 wood reduces time by 5%

Your response:"""
# Response will be parseable: "1.07 | HIGH | Quality 8 increases resistance"
```

### Pitfall 3: Missing Edge Case Guidance

**Problem**: LLM doesn't know how to handle special situations

```python
# ❌ BAD
prompt = f"Tournament result: {tournament_time if tournament_time else 'None'}"
# LLM sees "None" and doesn't know what to do
```

```python
# ✅ GOOD
if tournament_time:
    prompt += f"""
⚠️ TOURNAMENT CONTEXT
Tournament result: {tournament_time:.1f}s (PROVEN data)
Apply MINIMAL adjustment (±1-3% max)
"""
else:
    prompt += """
STANDARD CONTEXT
No tournament data available
Apply FULL quality adjustment (±2% per quality point)
"""
```

### Pitfall 4: Information Overload Without Hierarchy

**Problem**: Too much context, no prioritization

```python
# ❌ BAD - Wall of text
prompt = """You are a handicapper. Handicapping is complex. Wood has properties.
Competitors have histories. Baselines are calculated. Quality matters. Time-decay
is important. Sometimes we have tournament results. Species affect times. Diameter
matters too. Here's the data: baseline=40, quality=5, ..."""
```

```python
# ✅ GOOD - Clear hierarchy
prompt = """
⚠️ CRITICAL CONTEXT (Read First)
[Tournament weighting or special conditions]

COMPETITOR PROFILE
[Essential data]

BASELINE INTERPRETATION
[What baseline means]

WOOD SPECIFICATIONS
[Detailed wood data]

CALCULATION METHODOLOGY
[How to use the data]

RESPONSE REQUIREMENT
[Output format]
"""
```

### Pitfall 5: Outdated Prompts After System Changes

**Problem**: Code evolves but prompts don't

**Prevention**:
- Maintain a prompt update checklist alongside the code
- Link code changes to prompt impacts in PR descriptions
- Periodic prompt audits (quarterly)
- Automated tests that fail if prompts are stale

**Example**:
```python
# ❌ BAD - V4.4 added tournament weighting but prompt never updated
# LLM has no idea this feature exists

# ✅ GOOD - Prompt updated immediately when feature added
# Tournament context section added, explained to LLM
```

---

## Example Improvements

### Example 1: Time Prediction Prompt

**Before** (V1):
```python
prompt = f"""You are a woodchopping handicapper.

Competitor: {competitor_name}
Baseline: {baseline:.1f}s
Wood Species: {species}
Quality: {quality}/10

Adjust the baseline for quality. Return a multiplier.
"""
```

**Issues**:
- No explanation of what baseline includes
- Unclear output format
- No guidance on adjustment direction
- Missing context about system capabilities
- No tournament weighting support

**After** (V2):
```python
# Build conditional tournament context
tournament_section = ""
if tournament_weighted:
    tournament_section = f"""
⚠️ TOURNAMENT CONTEXT - CRITICAL ⚠️
Competitor already competed on THIS EXACT WOOD
Tournament result: {tournament_time:.1f}s (97% weight)
Your adjustment should be MINIMAL (±1-3% max)
"""

prompt = f"""You are a master woodchopping handicapper making precision predictions.

COMPETITOR PROFILE
Name: {competitor_name}
Baseline Time: {baseline:.1f} seconds
Confidence: {confidence}
{tournament_section}

BASELINE INTERPRETATION
- {"This baseline is HEAVILY WEIGHTED (97%) toward same-tournament result" if tournament_weighted else "This baseline assumes QUALITY 5 wood"}
- Baseline already includes: time-decay weighting, competitor skill, diameter effects
- Your task: Adjust ONLY for wood QUALITY (condition within species)

WOOD SPECIFICATIONS
Species: {species}
Quality: {quality}/10 (HIGHER = HARDER = SLOWER, LOWER = SOFTER = FASTER)

QUALITY ADJUSTMENT GUIDANCE
Quality deviation from baseline: {quality - 5:+d} points
Expected adjustment: ~{abs(quality-5)*2}% {"increase" if quality > 5 else "decrease" if quality < 5 else "no change"}

RESPONSE REQUIREMENT
Format: <multiplier> | <confidence> | <explanation>
Example: 1.07 | HIGH | Quality 8 increases resistance by 7%

Your response:"""
```

**Improvements**:
- ✓ Clear sections with headers
- ✓ Tournament context when applicable
- ✓ Baseline sophistication explained
- ✓ Explicit output format with example
- ✓ Adjustment guidance with calculation
- ✓ Critical information highlighted (⚠️)

### Example 2: Fairness Assessment Prompt

**Before** (V1):
```python
prompt = f"""Analyze handicap fairness.

Win rates:
{winner_data}

Target: {ideal_win_rate:.1f}% per competitor

Rate the fairness and explain any issues.
"""
```

**Issues**:
- No methodology explanation
- Missing competitor statistics (V5.0 feature)
- No guidance on rating scale
- Unclear what "explain issues" means
- No diagnostic framework

**After** (V2):
```python
# Build competitor stats section if available
stats_section = ""
if 'competitor_time_stats' in analysis:
    stats_lines = [f"  - {name}: mean={s['mean']:.1f}s, std_dev={s['std_dev']:.2f}s, consistency={s['consistency_rating']}"
                   for name, s in analysis['competitor_time_stats'].items()]
    stats_section = "\n\nPER-COMPETITOR STATISTICS:\n" + "\n".join(stats_lines)
    stats_section += """

CONSISTENCY ANALYSIS REQUIRED:
- Are there competitors with std_dev > 3.5s? (prediction may be wrong)
- Does high variance correlate with LOW confidence?
- Does ±3s model assumption hold for all competitors?
"""

prompt = f"""You are a master woodchopping handicapper analyzing fairness via Monte Carlo simulation.

HANDICAPPING GOAL
Create handicaps where ALL competitors have EQUAL win probability.
Skill level should NOT predict victory.

SIMULATION METHODOLOGY
- {num_simulations:,} races simulated
- ±3s absolute variance (same for all skill levels)
- Variance represents real factors: wood grain, technique, fatigue

SIMULATION RESULTS

ACTUAL WIN RATES:
{winner_data}

IDEAL: {ideal_win_rate:.2f}% per competitor

STATISTICAL MEASURES:
- Win Rate Spread: {win_rate_spread:.2f}% (max - min)
- Standard Deviation: {win_rate_std_dev:.2f}%

INDIVIDUAL COMPETITOR STATISTICS:
{stats_section}

FAIRNESS RATING SCALE:
- Excellent: <3% spread
- Very Good: 3-6% spread
- Good: 6-10% spread
- Fair: 10-15% spread
- Poor: >15% spread

YOUR ANALYSIS REQUIRED (5 sections):

1. OVERALL FAIRNESS RATING: [Excellent/Very Good/Good/Fair/Poor]

2. PATTERN DIAGNOSIS:
   - Is there systematic bias? (front marker advantage, back marker advantage, etc.)
   - Do biased competitors show unusual variance patterns?
   - Are high-variance competitors also biased?

3. ROOT CAUSE ANALYSIS:
   - Which predictions are likely inaccurate?
   - Is bias due to wood quality effects?
   - Are confidence levels correlated with accuracy?

4. SPECIFIC RECOMMENDATIONS:
   - Which competitors need manual review?
   - Suggested mark adjustments (be specific)

5. CONFIDENCE IN ASSESSMENT:
   - How reliable are these recommendations?
   - What uncertainties remain?

Your analysis:"""
```

**Improvements**:
- ✓ Clear analysis framework (5 required sections)
- ✓ Competitor statistics included (V5.0 feature)
- ✓ Explicit rating scale
- ✓ Diagnostic questions for systematic analysis
- ✓ Specific output structure enforced

---

## Maintenance Checklist

### When Adding New System Features

Use this checklist whenever adding features that affect predictions:

- [ ] **Identify Affected Prompts**
  - Which prompts reference this system component?
  - Does this change prediction methodology?
  - Does this add new context the LLM should know?

- [ ] **Update Prompt Content**
  - Add explanation of new feature
  - Update system capabilities list
  - Add conditional sections if feature is optional
  - Update examples to show new behavior

- [ ] **Update Prompt Callers**
  - Pass new parameters to prompt functions
  - Handle new response fields
  - Update error handling

- [ ] **Version the Prompts**
  - Increment version number
  - Extract to versioned file (if using file-based system)
  - Document changes in PROMPT_CHANGELOG.md

- [ ] **Test Thoroughly**
  - Run A/B comparison vs old prompt
  - Verify new context improves predictions
  - Check parse success rate
  - Validate edge cases

- [ ] **Update Documentation**
  - PROMPT_ENGINEERING_GUIDELINES.md (this file)
  - explanation_system_functions.py (user-facing docs)
  - SYSTEM_STATUS.md (capabilities list)

- [ ] **Monitor in Production**
  - Track prediction accuracy metrics
  - Collect judge feedback
  - Watch for unexpected behavior
  - Be ready to rollback if needed

### Quarterly Prompt Audit

Every 3 months, conduct comprehensive prompt audit:

- [ ] **Review System Changes**
  - What features were added since last audit?
  - What bugs were fixed that affect predictions?
  - Are prompts still accurate?

- [ ] **Check Prompt-Code Alignment**
  - Do prompts correctly describe system capabilities?
  - Are conditional sections being triggered correctly?
  - Are output formats still being parsed correctly?

- [ ] **Analyze Performance Metrics**
  - Has prediction accuracy improved/degraded?
  - Are confidence levels well-calibrated?
  - Which prompts have highest parse failure rates?

- [ ] **Collect Stakeholder Feedback**
  - Survey judges on prediction quality
  - Review manual adjustment frequency
  - Identify common complaints

- [ ] **Plan Improvements**
  - Prioritize prompt updates based on data
  - Schedule A/B tests for proposed changes
  - Document improvement roadmap

### Before Major Releases

- [ ] **Prompt Freeze**
  - No prompt changes 2 weeks before release
  - Ensures stability and testing time

- [ ] **Comprehensive Testing**
  - Run full test suite with all prompts
  - Validate against known-good scenarios
  - Test edge cases

- [ ] **Documentation Review**
  - All prompt versions documented?
  - CHANGELOG up to date?
  - User-facing docs synced?

- [ ] **Backup & Rollback Plan**
  - Can we quickly revert to previous prompts?
  - Are old versions tagged in git?
  - Do we have comparison baselines?

---

## Advanced Techniques

### Chain-of-Thought Prompting

**Technique**: Ask LLM to reason step-by-step before answering

**When to Use**: Complex decisions with multiple factors

**Example**:
```python
prompt = f"""
[...context...]

REASONING PROCESS (work through these steps):

Step 1: Assess baseline confidence
- Is tournament data available? (Yes/No)
- Is baseline from robust history? (>10 results)
- Conclusion: Baseline confidence is [VERY HIGH/HIGH/MEDIUM/LOW]

Step 2: Analyze quality deviation
- Quality {quality} vs baseline quality 5 = {quality-5:+d} point deviation
- Expected adjustment: {abs(quality-5)*2}% {"increase" if quality > 5 else "decrease"}
- Wood is {"harder" if quality > 5 else "softer"} than baseline assumption

Step 3: Determine adjustment magnitude
- If tournament data: Apply MINIMAL adjustment (±1-3%)
- If standard prediction: Apply FULL adjustment (~{abs(quality-5)*2}%)
- Decision: Use [MINIMAL/FULL] adjustment

Step 4: Calculate multiplier
- Starting from 1.00 (no change)
- Apply adjustment: 1.00 {"+" if quality > 5 else "-"} {abs(quality-5)*0.02:.2f}
- Final multiplier: [calculate]

Now provide your final answer in format: <multiplier> | <confidence> | <explanation>
"""
```

**Benefits**:
- Increases reasoning quality
- Makes LLM decisions more interpretable
- Reduces random errors

**Costs**:
- Increases output token usage
- Slower response times
- May be overkill for simple tasks

### Few-Shot Examples

**Technique**: Show LLM 2-3 examples of correct reasoning before asking it to perform task

**When to Use**: Complex tasks, new prompt patterns, edge cases

**Example**:
```python
prompt = f"""
[...context...]

EXAMPLE 1 (Standard prediction):
Input: Baseline 40s, Quality 8 (hard), Historical confidence HIGH
Reasoning: Quality 8 is +3 from baseline (quality 5)
          Expect 3×2% = 6% increase
          No tournament data, apply full adjustment
Output: 1.06 | HIGH | Quality 8 hard wood increases resistance by 6%

EXAMPLE 2 (Tournament weighted):
Input: Baseline 50s (tournament 50.3s @ 97%), Quality 5
Reasoning: Tournament result is PROVEN data on same wood
          Quality 5 = no deviation from baseline assumption
          Apply minimal adjustment (tournament dominates)
Output: 1.00 | VERY HIGH | Tournament result on same wood, no adjustment needed

EXAMPLE 3 (Soft wood):
Input: Baseline 35s, Quality 2 (soft), Historical confidence MEDIUM
Reasoning: Quality 2 is -3 from baseline (quality 5)
          Expect 3×2% = 6% decrease
          No tournament data, apply full adjustment
Output: 0.94 | MEDIUM | Quality 2 soft wood reduces resistance by 6%

NOW YOUR TURN:
Input: Baseline {baseline:.1f}s, Quality {quality}, {"Tournament " + str(tournament_time) + "s" if tournament_time else "No tournament data"}
Your reasoning and output:
"""
```

**Benefits**:
- Dramatically improves accuracy on complex tasks
- Teaches LLM the reasoning pattern
- Handles edge cases better

**Costs**:
- Increases input token usage significantly
- Longer prompts take more time to process
- Examples must be carefully chosen (bad examples teach bad patterns)

### Structured Input/Output (XML/JSON)

**Technique**: Use markup to clearly delineate sections

**When to Use**: Complex nested data, machine-parseable output required

**Example**:
```python
prompt = f"""
<task>Predict competitor cutting time with quality adjustment</task>

<competitor>
  <name>{competitor_name}</name>
  <baseline_time>{baseline:.1f}</baseline_time>
  <confidence>{confidence}</confidence>
  <tournament_result>{tournament_time if tournament_time else "null"}</tournament_result>
</competitor>

<wood>
  <species>{species}</species>
  <quality>{quality}</quality>
  <quality_interpretation>{"harder" if quality > 5 else "softer" if quality < 5 else "average"}</quality_interpretation>
</wood>

<instructions>
  Adjust baseline time for wood quality.
  {"Apply MINIMAL adjustment (±1-3%) due to tournament data." if tournament_time else "Apply FULL adjustment (~2% per quality point)."}
</instructions>

<output_format>
  <multiplier>float between 0.85 and 1.15</multiplier>
  <confidence>VERY HIGH | HIGH | MEDIUM | LOW</confidence>
  <explanation>one sentence, max 15 words</explanation>
</output_format>

Return your response in XML format matching the output_format schema.
"""
```

**Benefits**:
- Unambiguous data structure
- Easier to parse programmatically
- Reduces format errors

**Costs**:
- More verbose (higher token usage)
- LLM may not always follow XML structure perfectly
- Requires robust parsing on response

**Recommendation**: Use for Prompt 3+ (complex analysis), overkill for Prompt 1 (simple prediction)

---

## Model-Specific Considerations

### qwen2.5:32b (Current Model)

**Strengths**:
- Excellent mathematical reasoning
- Follows structured instructions well
- Good at numerical precision tasks
- Handles technical terminology accurately

**Weaknesses**:
- Can be overly literal (needs explicit guidance)
- May apply logic too rigidly (edge case handling)
- Less creative/narrative than other models

**Optimization Tips**:
- Provide explicit formulas and examples
- Use structured sections with clear headers
- Give numerical ranges for expected outputs
- Show step-by-step calculation processes

**Best Practices**:
```python
# ✅ GOOD for qwen2.5
"Quality deviation: +3 points. Expected adjustment: 3 × 2% = 6%"
"Multiply baseline by 1.06"

# ❌ BAD for qwen2.5
"Consider the quality and adjust appropriately"  # Too vague
```

### Future Model Upgrades

**When upgrading models**, re-test ALL prompts:

1. **Capture Baseline** (current model outputs)
2. **Run Test Suite** (new model with same prompts)
3. **Compare Outputs**:
   - Are predictions more/less accurate?
   - Is reasoning quality better/worse?
   - Do responses still parse correctly?
   - Are there new failure modes?
4. **Adjust Prompts** if needed (new model may need different style)
5. **Document Changes** in PROMPT_CHANGELOG.md

**Model-Specific Config**:
```python
# config.py
class LLMConfig:
    DEFAULT_MODEL = "qwen2.5:32b"
    MODEL_SPECIFIC_SETTINGS = {
        "qwen2.5:32b": {
            "style": "technical-structured",
            "token_limits": {
                "time_prediction": 50,
                "fairness": 5000,
                "championship": 800
            },
            "best_practices": [
                "Use explicit formulas",
                "Provide numerical examples",
                "Structure with headers"
            ]
        },
        "gpt-4o": {  # Future possibility
            "style": "conversational-guided",
            "token_limits": {
                "time_prediction": 100,
                "fairness": 6000,
                "championship": 1200
            },
            "best_practices": [
                "Can handle more ambiguity",
                "Better at narrative analysis",
                "Less rigid instruction following"
            ]
        }
    }
```

---

## Conclusion

Effective prompt engineering is **critical** to STRATHEX's prediction accuracy. Well-designed prompts:
- Communicate system intelligence to the LLM
- Prevent double-adjustments and logic errors
- Enable sophisticated features (tournament weighting, variance analysis)
- Build trust with judges through interpretable reasoning

**Key Takeaways**:
1. **Context is King** - LLM can't infer your system internals
2. **Structure Matters** - Clear sections, explicit instructions, examples
3. **Version Everything** - Track changes, test rigorously, document thoroughly
4. **Sync Documentation** - Update all docs when prompts change (STANDING ORDER)
5. **Test Before Deploy** - A/B test, capture baselines, validate metrics

**Next Steps**:
- Implement high-priority prompt improvements from audit
- Set up prompt versioning system
- Schedule quarterly prompt audits
- Train team on these guidelines

---

**Document Maintenance**:
- **Owner**: Primary system maintainer
- **Review Frequency**: Quarterly (or after major prompt changes)
- **Last Reviewed**: January 12, 2026
- **Next Review**: April 12, 2026

For questions or suggestions, document them in [PROMPT_CHANGELOG.md](PROMPT_CHANGELOG.md) or raise an issue in the GitHub repository.
