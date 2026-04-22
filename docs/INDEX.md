# Documentation Index

Complete guide to all documentation in the Woodchopping Handicap System.

---

## Project Structure

```
woodchopping-handicap-system/
├── MainProgramV5_2.py          # Main entry point
├── config.py                   # Configuration settings
├── explanation_system_functions.py  # Judge education wizard
├── woodchopping.xlsx           # Main data file
├── README.md                   # User guide
├── CLAUDE.md                   # Development guidelines
│
├── woodchopping/               # Core package (predictions, handicaps, simulation, ui)
├── tests/                      # Test suite
│   └── validation/             # Validation/backtesting tests
├── scripts/                    # Utility scripts (analysis, data processing)
├── data/                       # Data outputs
│   ├── results/                # CSV results, analysis outputs
│   └── backups/                # Excel backups
├── docs/                       # Documentation (you are here)
│   ├── solutions/              # Documented past solutions (bugs, best practices, workflows)
│   └── archive/                # Historical implementation reports
├── wiki/                       # Versioned source for the GitHub Wiki (publish via wiki/publish.sh)
├── reference/                  # Competition rules, QAA PDFs
└── saves/                      # Tournament state files (not tracked in git)
```

---

## Start Here

### 1. **[SYSTEM_STATUS.md](SYSTEM_STATUS.md)** - System Overview
**What**: Comprehensive status report of the entire system
**When to Read**: First time exploring the system, checking current capabilities

### 2. **[../README.md](../README.md)** - User Guide (Root Directory)
**What**: User manual and quick start guide
**When to Read**: Learning how to use the program

### 3. **[../CLAUDE.md](../CLAUDE.md)** - Project Architecture (Root Directory)
**What**: AI assistant guidelines and project architecture
**When to Read**: Understanding codebase structure, contributing to the project

---

## Technical Documentation

### **[ML_AUDIT_REPORT.md](ML_AUDIT_REPORT.md)** - ML Model Audit
ML model architecture, feature engineering, performance metrics

### **[HANDICAP_SYSTEM_EXPLAINED.md](HANDICAP_SYSTEM_EXPLAINED.md)** - System Explanation
How handicaps work, AAA rules, prediction methodology

### **[PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)** - Codebase Architecture
Module organization, file purposes, key functions

### **[CHECK_MY_WORK_FEATURE.md](CHECK_MY_WORK_FEATURE.md)** - Check My Work Validation
Judge validation system, cross-validation features

### **[QAA_INTERPOLATION_IMPLEMENTATION.md](QAA_INTERPOLATION_IMPLEMENTATION.md)** - QAA Interpolation
Quality/Age/Axe scaling logic, implementation details

---

## LLM & Prompt Engineering

### **[PROMPT_ENGINEERING_GUIDELINES.md](PROMPT_ENGINEERING_GUIDELINES.md)** - Prompt Guidelines
Core principles, STRATHEX-specific guidelines, testing procedures

### **[PROMPT_CHANGELOG.md](PROMPT_CHANGELOG.md)** - Prompt Version History
LLM prompt changes, rationale, versioning

---

## GitHub Wiki

The wiki is version-controlled in [wiki/](../wiki/) and published via `bash wiki/publish.sh`. 17 content pages covering the handicap pipeline, prediction methods, Monte Carlo fairness, tournament workflows, AAA/QAA rule compliance, data model, FAQ, and version history. Edit pages in `wiki/`, commit to the main repo, then run the publish script to sync to GitHub.

---

## Past Solutions

[solutions/](solutions/) — documented solutions to past problems, organized by category with YAML frontmatter (`module`, `tags`, `problem_type`). Written by the `/ce:compound` workflow; relevant when implementing or debugging in documented areas. See [solutions/README.md](solutions/README.md) for the full index and reading order for new contributors.

### Quick links

- **Architecture** — [STRATHMARK extraction (V6.0)](solutions/architecture-decisions/strathmark-extraction-v6.md), [QAA scaling removal](solutions/architecture-decisions/qaa-scaling-removal.md)
- **Best practices** — [prompt/feature parity discipline](solutions/best-practices/prompt-feature-parity.md), [judge UI simplicity](solutions/best-practices/judge-ui-simplicity-principle.md)
- **Data integrity** — [wood quality scale](solutions/data-integrity/wood-quality-scale-inversion.md), [sparse competitor data](solutions/data-integrity/sparse-competitor-data-fallback.md), [Excel Results schema](solutions/data-integrity/excel-results-schema-column-mismatch.md)
- **Runtime errors** — [Windows UNICODE/ASCII](solutions/runtime-errors/unicode-ascii-windows-terminal.md), [numpy polyfit DLASCLS](solutions/runtime-errors/numpy-polyfit-dlascls-sparse-data.md)
- **Test failures** — [pytest Ollama markers](solutions/test-failures/pytest-collection-ollama-markers-2026-04-06.md), [ML feature count mismatch](solutions/test-failures/ml-feature-count-mismatch.md)
- **Build errors** — [hatch direct-ref for strathmark](solutions/build-errors/hatch-allow-direct-references-2026-04-06.md)
- **Workflow issues** — [versioned wiki source](solutions/workflow-issues/versioned-wiki-source-2026-04-21.md)

---

## Archived Documentation

Historical implementation reports are in [archive/](archive/):
- BASELINE_V2_IMPLEMENTATION_SUMMARY.md
- BASELINE_V2_VALIDATION_REPORT.md
- LLM_PROMPT_AUDIT_2026.md
- ML_REDESIGN_IMPLEMENTATION_REPORT.md
- OPTION_5_10_IMPLEMENTATION.md
- PROMPT_UPDATE_SUMMARY_2026-01-12.md
- Tournament and Personnel Changes.md
- V5.2_UI_IMPROVEMENTS.md

---

## Quick Reference

### System Metrics (V5.2 - Jan 2026)

```
ML Model Performance:
- SB: MAE 2.55s, R² 0.989
- UH: MAE 2.35s, R² 0.878

Fairness Metrics:
- Target win rate spread: < 2%
- Absolute variance: ±3s for all competitors
- Time-decay half-life: 730 days (2 years)
```

---

## Contributing

When adding new documentation:
1. Place technical docs in `docs/` directory
2. Update this INDEX.md with new entries
3. Update [SYSTEM_STATUS.md](SYSTEM_STATUS.md) if system capabilities change
4. Update [README.md](../README.md) in root if user-facing changes
5. Archive outdated implementation reports in `docs/archive/`

---

**Maintained by**: Alex Kaper
**AI Assistant**: Claude (Anthropic)
**Last Updated**: April 2026
