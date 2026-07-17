"""Regression tests for bugs found in the codebase audit.

Each test reproduces a confirmed crash/leak that the audit fixes address.
All are isolated and never touch the production workbook.
"""

import pandas as pd

from woodchopping.strathmark_adapter import build_competitor_records
from woodchopping.ui.bracket_ui import render_match_box_compact


def test_render_match_box_compact_handles_tbd_competitors():
    """A pending match with None competitors must not crash (was TypeError on None[:28])."""
    match = {
        "match_id": "R2M1",
        "status": "pending",
        "competitor1": None,
        "competitor2": None,
        "seed1": "",
        "seed2": "",
        "time1": None,
        "time2": None,
        "winner": None,
    }
    # Must render without raising.
    render_match_box_compact(match)


def test_render_match_box_compact_normal_match():
    """A completed match still renders."""
    match = {
        "match_id": "R1M1",
        "status": "completed",
        "competitor1": "Al Axe",
        "competitor2": "Bo Saw",
        "seed1": 1,
        "seed2": 2,
        "time1": 25.0,
        "time2": 27.5,
        "winner": "Al Axe",
    }
    render_match_box_compact(match)


def test_build_competitor_records_defaults_nan_size_mm():
    """A NaN size_mm must not drop the row or crash — it defaults to 300."""
    df = pd.DataFrame(
        {
            "competitor_name": ["Al Axe", "Al Axe"],
            "event": ["SB", "SB"],
            "raw_time": [30.0, 31.0],
            "species": ["S01", "S01"],
            "size_mm": [300.0, float("nan")],  # second row has a blank diameter
            "quality": [5, 5],
            "date": pd.to_datetime(["2024-01-01", "2024-02-01"]),
            "heat_id": ["H1", "H2"],
        }
    )
    records = build_competitor_records(["Al Axe"], df)
    assert len(records) == 1
    history = records[0].history
    # Both rows survive (neither dropped), and no NaN diameter leaks through.
    assert len(history) == 2
    for h in history:
        assert h.diameter_mm == h.diameter_mm  # not NaN
    assert any(h.diameter_mm == 300.0 for h in history)
