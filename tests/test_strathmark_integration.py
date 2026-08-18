"""Regression tests for the STRATHEX -> STRATHMARK v2 boundary."""

from __future__ import annotations

import pandas as pd

import woodchopping.strathmark_adapter as adapter
from woodchopping.simulation.fairness import format_ai_assessment


def _history_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "competitor_name": [
                "Alice Axe",
                "Alice Axe",
                "Bob Block",
                "Bob Block",
            ],
            "event": ["SB", "SB", "SB", "SB"],
            "raw_time": [30.0, 31.0, 40.0, 39.0],
            "species": ["S01", "S01", "S01", "S01"],
            "size_mm": [300.0, 300.0, 300.0, 300.0],
            "quality": [5, 5, 5, 5],
            "date": pd.to_datetime(["2025-01-01", "2025-02-01", "2025-01-01", "2025-02-01"]),
        }
    )


def test_enrich_results_with_roster_fills_gender_without_mutating_inputs():
    results = _history_df()
    roster = pd.DataFrame(
        {
            "competitor_name": ["Alice Axe", "Bob Block"],
            "gender": ["F", "Male"],
        }
    )

    enriched = adapter.enrich_results_with_roster(results, roster)

    assert "gender" not in results.columns
    assert enriched.loc[enriched["competitor_name"] == "Alice Axe", "gender"].eq("F").all()
    assert enriched.loc[enriched["competitor_name"] == "Bob Block", "gender"].eq("M").all()


def test_format_ai_assessment_restores_existing_analysis_screen(capsys):
    format_ai_assessment(
        "FAIRNESS RATING:\n"
        "This is a deliberately long assessment sentence that should wrap "
        "without changing the words or requiring any STRATHMARK formatter.",
        width=50,
    )

    output = capsys.readouterr().out
    assert "FAIRNESS RATING:" in output
    assert "deliberately long assessment sentence" in output
    assert max(len(line) for line in output.splitlines()) <= 50
