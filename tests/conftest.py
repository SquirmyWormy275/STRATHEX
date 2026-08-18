"""Pytest configuration for STRATHEX tests.

Some files in tests/ and tests/validation/ are standalone benchmark / audit
scripts whose top-level functions happen to start with ``test_``. They are
not release-gate tests. Legacy predictor tests that read the tracked production
workbook are also excluded; v7 integration tests use synthetic fixtures only.
"""

from __future__ import annotations

collect_ignore_glob = [
    "test_baseline_hybrid.py",
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
