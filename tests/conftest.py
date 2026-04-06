"""Pytest configuration for STRATHEX tests.

Most files in tests/ and tests/validation/ are standalone benchmark / audit
scripts whose top-level functions happen to start with ``test_``. They are
not pytest test cases — pytest collection trips over their custom positional
parameters. We exclude them at collection time so the genuine unit-test
modules (currently only ``test_baseline_hybrid.py``) run cleanly in CI.
"""

from __future__ import annotations

from pathlib import Path

import pytest

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

# Tests in test_baseline_hybrid.py that call load_results_df() / load_wood_data()
# require ``woodchopping.xlsx`` in the project root. That file is the production
# database and is intentionally not tracked in git, so it is absent in CI.
# Skip these specific tests when the file is missing rather than failing.
_DATA_DEPENDENT_TESTS = {
    "test_fit_and_cache_baseline_v2_model",
    "test_predict_baseline_v2_hybrid_with_cache",
    "test_predict_baseline_v2_hybrid_tournament_weighting",
    "test_predict_baseline_v2_hybrid_quality_adjustment",
    "test_predict_baseline_v2_hybrid_new_competitor",
    "test_predict_baseline_v2_hybrid_convergence_disabled",
    "test_cache_persistence",
    "test_prediction_consistency",
}


def pytest_collection_modifyitems(config, items):
    repo_root = Path(__file__).resolve().parent.parent
    if (repo_root / "woodchopping.xlsx").exists():
        return
    skip = pytest.mark.skip(reason="woodchopping.xlsx not present (production data, not tracked in git)")
    for item in items:
        if item.name in _DATA_DEPENDENT_TESTS:
            item.add_marker(skip)
