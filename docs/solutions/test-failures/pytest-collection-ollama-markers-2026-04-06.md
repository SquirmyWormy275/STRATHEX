---
title: Pytest collection fails in CI due to script-style tests, missing data file, and unmarked Ollama tests
date: 2026-04-21
category: test-failures
module: testing
problem_type: test_failure
component: testing_framework
symptoms:
  - "Pytest collection errors on files whose top-level `test_*` functions take positional parameters"
  - "Tests importing `load_results_df()` / `load_wood_data()` fail when `woodchopping.xlsx` is absent in CI"
  - "`tests/validation/test_model_comparison.py` hits a live Ollama HTTP endpoint that does not exist on CI runners"
root_cause: test_isolation
resolution_type: test_fix
severity: high
related_components:
  - development_workflow
  - tooling
tags: [pytest, conftest, ollama, ci, test-collection, marker, fixtures]
---

# Pytest collection fails in CI due to script-style tests, missing data file, and unmarked Ollama tests

## Problem
Setting up CI for STRATHEX surfaced three independent test-collection failures that all needed fixing together: (1) several files in `tests/` are standalone benchmark scripts whose `test_*` functions take positional parameters pytest cannot inject; (2) `tests/test_baseline_hybrid.py` reads `woodchopping.xlsx` (the production database, intentionally untracked in git); and (3) `tests/validation/test_model_comparison.py` hits a local Ollama HTTP endpoint that does not exist on GitHub-hosted runners.

## Symptoms
- Collection errors on files like `test_both_events.py`, `test_check_my_work.py`, `test_stand_optimization.py` — pytest reports missing fixtures for positional arguments
- `FileNotFoundError: woodchopping.xlsx` raised during test body, not a skip
- `requests.ConnectionError: localhost:11434` in `test_model_comparison.py` — no Ollama service on CI

## What Didn't Work
- Running `pytest tests/ -v --tb=line` alone as a smoke test. Collection errors on script-style files masked the data-dependent and Ollama-dependent failures; they only became visible after the first class of failures was resolved
- Adding per-test `@pytest.mark.ollama` decorators to `test_model_comparison.py`. The whole module requires Ollama — module-level `pytestmark = pytest.mark.ollama` is cleaner and doesn't miss functions added later
- Considering a rewrite of the script-style test files into real pytest cases. Those files are benchmark / audit scripts that only happen to use `test_*` naming; rewriting them had no value relative to excluding them at collection time

## Solution
Added [tests/conftest.py](../../../tests/conftest.py) with two mechanisms:

```python
from pathlib import Path
import pytest

# 1. Skip script-style files at collection time
collect_ignore_glob = [
    "test_both_events.py",
    "test_check_my_work.py",
    "test_monte_carlo_stats.py",
    "test_stand_optimization.py",
    "test_uh_predictions.py",
    "validation/test_baseline_v2_*.py",
    "validation/test_enhanced_features.py",
    "validation/test_model_comparison.py",
    "validation/test_xgboost_upgrade.py",
]

# 2. Skip data-dependent tests in test_baseline_hybrid.py when
#    woodchopping.xlsx is absent (production data, not in git)
_DATA_DEPENDENT_TESTS = {
    "test_fit_and_cache_baseline_v2_model",
    "test_predict_baseline_v2_hybrid_with_cache",
    # ... (8 total)
}

def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    repo_root = Path(__file__).resolve().parent.parent
    if (repo_root / "woodchopping.xlsx").exists():
        return
    skip = pytest.mark.skip(reason="woodchopping.xlsx not present (production data, not tracked in git)")
    for item in items:
        if item.name in _DATA_DEPENDENT_TESTS:
            item.add_marker(skip)
```

Marked the Ollama-dependent module with a module-level marker:

```python
# tests/validation/test_model_comparison.py
import pytest

# Entire module requires a local Ollama instance — CI skips it via -m "not ollama".
pytestmark = pytest.mark.ollama
```

Registered both markers in [pyproject.toml](../../../pyproject.toml):

```toml
[tool.pytest.ini_options]
markers = [
    "ollama: tests that require a local Ollama instance (skipped in CI)",
    "strathmark: tests that exercise the strathmark engine directly",
]
```

CI runs `pytest tests/ -v --tb=short -m "not ollama" --cov=woodchopping --cov-report=term-missing`, which now collects cleanly: 11 passed, 8 skipped, 0 errors.

## Why This Works
Pytest offers three layers of test exclusion, and each problem needs the right one:

1. **`collect_ignore_glob`** excludes files at collection time, before pytest inspects their functions. This is correct for script-style files that happen to use `test_*` naming but aren't real test cases.
2. **`pytest_collection_modifyitems`** lets you add markers (including `skip`) to already-collected items based on arbitrary runtime conditions — ideal for "skip if production data file is absent" where the file's presence is a runtime property, not a file-path pattern.
3. **Module-level `pytestmark`** applies a marker to every function in a file. Combined with the CLI `-m "not ollama"` filter, it lets contributors opt out of an entire class of tests in one line, without touching each function. Registering markers in `pyproject.toml` avoids `PytestUnknownMarkWarning` at collection.

## Prevention
- When a new test file is added that depends on external services (Ollama, a database, the network), apply a module-level marker at the top: `pytestmark = pytest.mark.ollama` (or a new marker registered in `pyproject.toml`). Per-test decorators will be forgotten on functions added later
- When a test reads a file that isn't shipped in the repo (production data, user config), skip cleanly via `pytest_collection_modifyitems` or an autouse fixture. Do not raise `FileNotFoundError` from a test body
- New markers must be registered in `[tool.pytest.ini_options].markers` in the same commit. Unregistered markers emit `PytestUnknownMarkWarning`, which clutters output and hides real typos
- Script-style files in `tests/` are a smell. If new ones are added, prefer `scripts/` or `benchmarks/` directories so pytest never looks at them. The current `collect_ignore_glob` list is a holding pattern, not a permanent solution

## Related Issues
- [README.md CI/CD section](../../../README.md) — documents the `-m "not ollama"` filter
- [CLAUDE.md](../../../CLAUDE.md) — "Tests that need a local Ollama instance must be marked `@pytest.mark.ollama`" (standing rule)
- Global CLAUDE.md "Test Isolation" rule — "Tests MUST NEVER write to or pollute the production database" (justifies the `woodchopping.xlsx`-absent skip)
- [.github/workflows/ci.yml](../../../.github/workflows/ci.yml) — consumer of the `ollama` marker
- [docs/PROJECT_STRUCTURE.md](../PROJECT_STRUCTURE.md) — may need refresh to mention the new `tests/conftest.py` and marker strategy
- Commit 9ee59c8 — the conftest + marker changes
