"""Regression tests for Excel + ResultStore prediction history."""

from __future__ import annotations

import pandas as pd

import woodchopping.handicaps.calculator as calculator
from woodchopping.data.history_merge import merge_result_history


def _excel_history() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "competitor_name": ["Alice Axe", "Bob Block"],
            "event": ["SB", "UH"],
            "raw_time": [30.0, 42.5],
            "species": ["S01", "S03"],
            "size_mm": [300.0, 275.0],
            "quality": [5, 6],
            "heat_id": ["H1", "H2"],
            "date": pd.to_datetime(["2026-01-01", "2026-01-02"]),
        }
    )


def test_merge_history_deduplicates_startup_migration_rows():
    excel = _excel_history()
    store = pd.DataFrame(
        {
            "competitor_name": ["alice axe", "Carol Chop"],
            "event_code": ["sb", "SB"],
            "raw_time": [30.0, 37.25],
            "species": ["S01", "S01"],
            "size_mm": [300.0, 300.0],
            "quality": [5, 5],
            "heat_id": ["h1", "H3"],
            "result_date": [None, "2026-01-03"],
        }
    )

    merged = merge_result_history(excel, store)

    assert len(merged) == 3
    assert set(merged["competitor_name"]) == {
        "Alice Axe",
        "Bob Block",
        "Carol Chop",
    }
    # Excel is canonical on collisions and retains its dated row.
    alice = merged[merged["competitor_name"] == "Alice Axe"].iloc[0]
    assert alice["date"] == pd.Timestamp("2026-01-01")


def test_merge_history_normalizes_store_schema_and_event_case():
    store = pd.DataFrame(
        {
            "competitor_name": ["Alice Axe"],
            "event_code": ["uh"],
            "time_seconds": [29.5],
            "species": ["S03"],
            "diameter_mm": [275],
            "quality": [5],
            "result_date": ["2026-02-01"],
        }
    )

    merged = merge_result_history(None, store)

    assert merged.loc[0, "event"] == "UH"
    assert merged.loc[0, "raw_time"] == 29.5
    assert merged.loc[0, "size_mm"] == 275
    assert merged.loc[0, "heat_id"] == ""
    assert merged.loc[0, "date"] == pd.Timestamp("2026-02-01")


def test_merge_history_returns_independent_copy():
    excel = _excel_history()
    merged = merge_result_history(excel, None)

    merged.loc[0, "raw_time"] = 999.0

    assert excel.loc[0, "raw_time"] == 30.0


def test_live_calculation_uses_store_only_history(monkeypatch):
    excel = _excel_history().iloc[[0]].copy()
    store_only = pd.DataFrame(
        {
            "competitor_name": ["Alice Axe"],
            "event": ["SB"],
            "raw_time": [31.5],
            "species": ["S01"],
            "size_mm": [300.0],
            "quality": [5],
            "heat_id": ["H4"],
            "result_date": ["2026-01-04"],
        }
    )

    class FakeStore:
        def get_all_as_dataframe(self):
            return store_only

    captured = {}

    monkeypatch.setattr(calculator, "get_store", lambda: FakeStore())
    monkeypatch.setattr(
        calculator,
        "standardize_results_data",
        lambda frame: (frame, []),
    )
    heat = pd.DataFrame(
        {
            "competitor_name": ["Alice Axe"],
            "gender": ["F"],
        }
    )
    monkeypatch.setattr(calculator, "load_competitors_df", lambda: heat.copy())
    monkeypatch.setattr(
        calculator,
        "enrich_results_with_roster",
        lambda results, roster: results,
    )
    monkeypatch.setattr(calculator, "build_gender_map", lambda *args: {})

    def fake_build_records(names, results, **kwargs):
        captured["names"] = names
        captured["results"] = results
        return ["record"]

    monkeypatch.setattr(calculator, "build_competitor_records", fake_build_records)
    monkeypatch.setattr(calculator, "build_wood_profile", lambda *args: "wood")
    monkeypatch.setattr(calculator, "load_wood_data", lambda: pd.DataFrame())
    monkeypatch.setattr(
        calculator,
        "calculate_handicap_results",
        lambda **kwargs: [
            {
                "name": "Alice Axe",
                "mark": 3,
                "predicted_time": 30.0,
            }
        ],
    )

    output = calculator.calculate_ai_enhanced_handicaps(
        heat,
        "S01",
        300,
        5,
        "SB",
        excel,
    )

    assert output is not None
    assert captured["names"] == ["Alice Axe"]
    assert len(captured["results"]) == 2
    assert set(captured["results"]["raw_time"]) == {30.0, 31.5}
