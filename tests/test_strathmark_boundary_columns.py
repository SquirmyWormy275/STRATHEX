"""Regression tests for alias collisions at the STRATHMARK boundary."""

from __future__ import annotations

import pandas as pd

from woodchopping.strathmark_adapter import prepare_results_for_strathmark


def test_competitor_id_and_name_do_not_collapse_into_duplicate_columns():
    frame = pd.DataFrame(
        {
            "competitor_id": ["C001", "C002"],
            "competitor_name": ["Alice", "Bob"],
            "event": ["SB", "UH"],
            "raw_time": [30.0, 40.0],
            "size_mm": [300.0, 275.0],
            "species": ["S01", "S03"],
            "date": pd.to_datetime(["2026-01-01", "2026-02-01"]),
        }
    )

    prepared = prepare_results_for_strathmark(frame)
    assert prepared.columns.is_unique
    assert prepared["competitor_name"].tolist() == ["Alice", "Bob"]
    assert prepared["competitor_id"].tolist() == ["C001", "C002"]
    assert "date" in prepared.columns or "result_date" in prepared.columns


def test_alias_values_fill_missing_canonical_cells_without_overwriting_names():
    frame = pd.DataFrame(
        [
            ["Alice", "C001", 30.0, None, "2026-01-01"],
            [None, "C002", None, 41.0, "2026-02-01"],
        ],
        columns=["competitor_name", "competitor_id", "raw_time", "time", "date"],
    )

    prepared = prepare_results_for_strathmark(frame)

    assert prepared["competitor_name"].tolist()[0] == "Alice"
    assert pd.isna(prepared["competitor_name"].tolist()[1])
    assert prepared["competitor_id"].tolist() == ["C001", "C002"]
    assert prepared["raw_time"].tolist() == [30.0, 41.0]


def test_synthetic_history_is_safe_for_engine_normalization():
    history = pd.DataFrame(
        {
            "competitor_id": ["C001", "C002"],
            "competitor_name": ["Alice", "Bob"],
            "event": ["SB", "UH"],
            "raw_time": [30.0, 40.0],
            "size_mm": [300.0, 275.0],
            "species": ["S01", "S03"],
            "date": ["2026-01-01", "2026-02-01"],
        }
    )

    prepared = prepare_results_for_strathmark(history)
    assert len(prepared) == len(history)
    assert prepared.columns.is_unique
    assert isinstance(prepared["competitor_name"], pd.Series)
    assert prepared["competitor_name"].notna().all()
