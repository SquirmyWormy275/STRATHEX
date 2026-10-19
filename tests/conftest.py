"""Pytest configuration for STRATHEX tests.

Some files in tests/ and tests/validation/ are standalone benchmark / audit
scripts whose top-level functions happen to start with ``test_``. They are
not release-gate tests. Legacy predictor tests that read the tracked production
workbook are also excluded; v7 integration tests use synthetic fixtures only.
"""

from __future__ import annotations

import os

import pytest

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


@pytest.fixture(autouse=True)
def private_windows_test_root(request):
    """Provision only pytest's disposable synthetic storage directory."""
    if os.name == "nt":
        from strathmark.private_storage import private_directory

        private_directory(request.getfixturevalue("tmp_path"))
