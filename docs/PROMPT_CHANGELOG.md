# STRATHEX LLM Prompt Changelog

This document tracks all changes to LLM prompts used in the STRATHEX Woodchopping Handicap System.

**Purpose**: Maintain version history for prompt engineering, enable rollback, document improvement rationale
**Update Frequency**: Every time a prompt is modified
**Owner**: System maintainer

---

## Format Guidelines

Each entry should include:
- **Prompt Name & Version**: Which prompt and version number
- **Date**: When change was implemented
- **Changes**: Bullet list of modifications
- **Why**: Rationale for changes
- **Impact**: Expected or measured improvement
- **Testing**: How changes were validated
- **Rolled Back**: If and why rollback occurred

---

## Changelog

### time_prediction v2.0 (2026-01-12)

**Prompt**: Time Prediction (LLM Quality Adjustment)
**Location**: `woodchopping/predictions/ai_predictor.py`
**Function**: `predict_competitor_time_with_ai()`

**Changes**:
1. ✅ **Added tournament result weighting context section**
   - Conditional `⚠️ TOURNAMENT CONTEXT` section when `tournament_results` parameter passed
   - Explains 97% same-wood weighting vs 3% historical
   - Instructs LLM to apply MINIMAL adjustment (±1-3%) instead of standard adjustment
   - Shows calculation: `Baseline = (Tournament × 97%) + (Historical × 3%)`

2. ✅ **Added tournament_results parameter to function signature**
   - Previously function had no access to tournament data
   - Now receives `Optional[Dict[str, float]]` tournament_results parameter
   - Applies 97/3 weighting before passing baseline to LLM
   - Upgrades confidence to "VERY HIGH" when tournament data used

3. ✅ **Updated BASELINE INTERPRETATION section**
   - Dynamic text based on whether tournament weighted
   - "This baseline is HEAVILY WEIGHTED (97%) toward same-tournament result"
   - "Apply MINIMAL adjustment - tournament result already reflects wood characteristics"

4. ✅ **Updated prediction_aggregator.py to pass tournament_results**
   - Modified `get_all_predictions()` to pass tournament data to LLM predictor
   - Added `tournament_weighted` flag to LLM prediction metadata
   - Ensures consistency with Baseline V2 (which already had this feature)

**Why**:
- **Critical V4.4 Feature Not Communicated**: Tournament result weighting (97/3 split) was implemented in Baseline V2 but LLM predictor had no awareness of it
- **Prevents Over-Adjustment**: Without context, LLM would apply standard ±2%/point quality adjustments even when wood characteristics were PROVEN via tournament result
- **Trust Signal Missing**: LLM didn't know tournament data = highest confidence possible
- **Feature Parity**: Baseline V2 and ML had tournament awareness, but LLM predictor didn't

**Impact**:
- **Expected**: 15-20% improvement in semis/finals prediction accuracy
- **Expected**: Reduction in manual adjustments needed by judges
- **Expected**: Better confidence calibration (VERY HIGH vs HIGH)
- **Expected**: More conservative quality adjustments when tournament data available
- **Measured**: [To be updated after production validation]

**Testing**:
- **Unit Tests**: Added test cases for tournament_weighted = True/False
- **Integration**: Verified tournament_results flows from tournament state → aggregator → LLM predictor
- **A/B Comparison**: [To be conducted with 10 tournament scenarios]
  - Baseline: V1 predictions without tournament context
  - Test: V2 predictions with tournament context
  - Metrics: Prediction MAE, confidence calibration, judge satisfaction

**Rolled Back**: No

**Related Issues**: Fixes gap identified in LLM_PROMPT_AUDIT_2026.md (Critical Issue #1)

---

### fairness_assessment v2.0 (2026-01-12)

**Prompt**: Fairness Assessment (Monte Carlo Analysis)
**Location**: `woodchopping/simulation/fairness.py`
**Function**: `get_ai_assessment_of_handicaps()`

**Changes**:
1. ✅ **Added INDIVIDUAL COMPETITOR TIME STATISTICS section**
   - Conditional section when `competitor_time_stats` present in analysis dict
   - Displays per-competitor mean, std_dev, min, max, percentiles, consistency rating
   - Provides consistency rating thresholds (Very High ≤ 2.5s, High ≤ 3.0s, Moderate ≤ 3.5s, Low > 3.5s)
   - Explains variance model validation (±3s assumption)

2. ✅ **Added CONSISTENCY ANALYSIS REQUIRED subsection**
   - Explicitly instructs LLM to analyze variance patterns
   - Asks specific diagnostic questions:
     - Are there competitors with std_dev > 3.5s?
     - Does high variance correlate with LOW confidence predictions?
     - Are there competitors with surprisingly tight clustering (std_dev < 2.5s)?
     - Does ±3s model hold across all competitors?
     - Do biased competitors also show unusual variance patterns?

3. ✅ **Restructured FINISH TIME ANALYSIS section**
   - Moved finish time aggregates above individual stats
   - Better information flow: aggregates → individual → patterns
   - Improved readability

**Why**:
- **V5.0 Feature Not Being Analyzed**: Monte Carlo simulator was upgraded to track individual competitor time statistics, but fairness assessment prompt never updated
- **Valuable Diagnostic Data Wasted**: Competitor variance patterns can reveal:
  - Inaccurate predictions (high variance suggests wrong baseline)
  - Confidence calibration issues (LOW confidence should correlate with high variance)
  - Model assumption violations (std_dev >> 3.0s means ±3s model doesn't hold)
- **Systematic Analysis Gap**: LLM was generating fairness assessments without considering consistency patterns

**Impact**:
- **Expected**: Better root cause diagnosis for biased handicaps
- **Expected**: Identification of prediction accuracy issues via variance analysis
- **Expected**: Validation of ±3s variance model assumption
- **Expected**: Correlation analysis between confidence and actual variance
- **Measured**: [To be updated after production validation]

**Testing**:
- **Unit Tests**: Verified competitor_time_stats properly formatted and included in prompt
- **Integration**: Checked that `run_monte_carlo_simulation()` returns stats dict
- **Visual Inspection**: Reviewed generated prompts to ensure stats section appears correctly
- **A/B Comparison**: [To be conducted with 5 fairness scenarios]
  - Baseline: V1 assessments without competitor stats
  - Test: V2 assessments with competitor stats
  - Metrics: Diagnostic quality, issue identification rate, recommendation relevance

**Rolled Back**: No

**Related Issues**: Fixes gap identified in LLM_PROMPT_AUDIT_2026.md (Critical Issue #2)

---

## Planned Future Updates

### time_prediction v3.0 (Planned)
**Proposed Changes**:
- Add adaptive time-decay explanation (365/730/1095-day half-lives)
- Add Baseline V2 architecture context (hierarchical regression, shrinkage, etc.)
- Add QAA validation context for species adjustments

**Priority**: HIGH
**Estimated Impact**: Medium (10-15% improvement)
**Target Date**: Q1 2026

---

### fairness_assessment v3.0 (Planned)
**Proposed Changes**:
- Add prediction method metadata to competitor details
- Add event type context (handicap vs championship)
- Add multi-event tournament context (optional)

**Priority**: MEDIUM
**Estimated Impact**: Low-Medium (5-10% improvement)
**Target Date**: Q2 2026

---

### championship_analysis v2.0 (Planned)
**Proposed Changes**:
- Add prediction confidence context
- Add wood quality impact on race dynamics
- Optional: Add historical head-to-head records

**Priority**: MEDIUM
**Estimated Impact**: Medium (better narrative quality, more insightful analysis)
**Target Date**: Q2 2026

---

## Version History Summary

| Prompt | Current Version | Last Updated | Major Changes Since v1 |
|--------|----------------|--------------|-------------------------|
| time_prediction | v2.0 | 2026-01-12 | +Tournament context, +tournament_results param |
| fairness_assessment | v2.0 | 2026-01-12 | +Competitor time statistics, +consistency analysis |
| championship_analysis | v1.0 | 2025-12-XX | Initial version (V5.0 feature) |

---

## Rollback Procedures

If a prompt update causes issues in production:

### Immediate Rollback (Emergency)

```python
# In affected file (e.g., ai_predictor.py)
# Comment out new prompt, uncomment old prompt

# OLD PROMPT (V1) - Rollback version
# prompt = f"""...[v1 content]..."""

# NEW PROMPT (V2) - Current version (DISABLED for rollback)
prompt = f"""...[v2 content]..."""  # ← Comment this out

# Revert to:
prompt = f"""...[v1 content]..."""  # ← Uncomment v1
```

### Systematic Rollback (Planned)

```bash
# 1. Identify commit with problematic prompt
git log --grep="Prompt:" --oneline

# 2. Revert specific file to previous version
git checkout <commit-hash> -- woodchopping/predictions/ai_predictor.py

# 3. Test rollback
python -m pytest tests/

# 4. Commit rollback
git commit -m "Rollback: Revert time_prediction to v1 due to [issue]

See PROMPT_CHANGELOG.md for details"

# 5. Document in changelog
# Add "Rolled Back: Yes - [reason]" to affected entry
```

### Post-Rollback Actions

- [ ] Update PROMPT_CHANGELOG.md with rollback reason
- [ ] Document issue that caused rollback
- [ ] Create GitHub issue to track fix
- [ ] Plan revised prompt update (if applicable)
- [ ] Notify stakeholders (judges) if production affected

---

## Testing Standards

### Minimum Testing Requirements for Prompt Changes

Before deploying prompt updates to production:

1. **Unit Tests**
   - ✅ Function signature changes tested
   - ✅ Parameter passing verified
   - ✅ Edge cases handled (None values, empty dicts, etc.)

2. **Integration Tests**
   - ✅ Data flows correctly through call chain
   - ✅ Conditional sections trigger appropriately
   - ✅ Response parsing succeeds

3. **A/B Testing** (Recommended)
   - Capture baseline outputs (current prompt)
   - Run test suite with new prompt
   - Compare metrics: accuracy, consistency, parse rate
   - Document results in changelog

4. **Visual Inspection**
   - Print example prompts to verify formatting
   - Check section ordering and hierarchy
   - Validate conditional sections appear correctly
   - Ensure no formatting bugs (extra newlines, missing indents)

5. **Production Monitoring** (Post-deployment)
   - Track prediction accuracy metrics
   - Monitor parse failure rates
   - Collect judge feedback
   - Watch for unexpected behavior

---

## Documentation Sync Checklist

When updating prompts, ensure these files are updated:

- [x] **PROMPT_CHANGELOG.md** (this file)
- [ ] **PROMPT_ENGINEERING_GUIDELINES.md** (if patterns change)
- [ ] **LLM_PROMPT_AUDIT_2026.md** (mark issues as resolved)
- [ ] **explanation_system_functions.py** (if user-facing behavior changes)
- [ ] **SYSTEM_STATUS.md** (update capabilities/improvements)
- [ ] **README.md** (if major user-visible changes)

---

## Contact & Maintenance

**Primary Owner**: Alex Kaper
**Secondary Contact**: [Add if applicable]
**Last Comprehensive Audit**: January 12, 2026
**Next Scheduled Audit**: April 12, 2026 (Quarterly)

For questions, issues, or proposed updates, create an issue in the GitHub repository with label `prompt-engineering`.

---

## Appendix: Prompt Locations

Quick reference for finding prompts in codebase:

| Prompt Purpose | File | Function | Line Range |
|----------------|------|----------|------------|
| Time Prediction | `woodchopping/predictions/ai_predictor.py` | `predict_competitor_time_with_ai()` | ~186-370 |
| Fairness Assessment | `woodchopping/simulation/fairness.py` | `get_ai_assessment_of_handicaps()` | ~210-390 |
| Championship Analysis | `woodchopping/simulation/fairness.py` | `get_championship_race_analysis()` | ~610-680 |
| Prediction Analysis | `woodchopping/predictions/prediction_aggregator.py` | `generate_prediction_analysis_llm()` | ~595-644 |

*Line ranges are approximate and may shift with code changes.*
