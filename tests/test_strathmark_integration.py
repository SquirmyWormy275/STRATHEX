"""Regression tests for the STRATHEX -> STRATHMARK integration boundary."""

from __future__ import annotations

from types import SimpleNamespace

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


def test_build_records_preserves_gender_and_existing_97_percent_weight_policy():
    results = adapter.enrich_results_with_roster(
        _history_df(),
        pd.DataFrame(
            {
                "competitor_name": ["Alice Axe"],
                "gender": ["F"],
            }
        ),
    )

    records = adapter.build_competitor_records(
        ["Alice Axe"],
        results,
        tournament_results={"alice axe": 28.25},
        gender_map={"Alice Axe": "F"},
    )

    assert len(records) == 1
    record = records[0]
    assert record.gender == "F"
    assert record.tournament_time == 28.25
    assert record.num_tournament_rounds == 4
    assert len(record.history) == 2


def test_calculation_trains_ml_selects_by_expected_error_and_reuses_predictions(monkeypatch):
    calls = {
        "train": [],
        "all_predictions": [],
        "select": [],
        "calculator": [],
    }

    class FakeMLModel:
        def train(self, results_df, wood_df):
            calls["train"].append((results_df, wood_df, self))
            return True

    def prediction(value, method, confidence="HIGH"):
        return SimpleNamespace(
            value=value,
            method=method,
            confidence=confidence,
            explanation=f"{method} prediction",
            metadata={"source": method},
        )

    def fake_get_all_predictions(
        record,
        wood,
        event_code,
        wood_data_df=None,
        results_df=None,
        ml_model=None,
        llm_client=None,
    ):
        calls["all_predictions"].append(
            {
                "record": record,
                "wood": wood,
                "event_code": event_code,
                "wood_df": wood_data_df,
                "results_df": results_df,
                "ml_model": ml_model,
                "llm_client": llm_client,
            }
        )
        offset = 0.0 if record.name == "Alice Axe" else 10.0
        return {
            "manual": None,
            "llm": prediction(32.0 + offset, "llm", "MEDIUM"),
            "ml": prediction(30.0 + offset, "ml", "HIGH"),
            "baseline": prediction(34.0 + offset, "baseline", "MEDIUM"),
            "panel": prediction(50.0 + offset, "panel", "VERY LOW"),
        }

    def fake_select_best_prediction(all_predictions):
        calls["select"].append(all_predictions)
        return all_predictions["ml"]

    class FakeCalculator:
        def __init__(self, **kwargs):
            calls["calculator"].append({"init": kwargs})
            self.kwargs = kwargs

        def calculate(
            self,
            competitors,
            wood,
            event_code,
            tournament_results=None,
            manual_overrides=None,
        ):
            calls["calculator"].append(
                {
                    "competitors": competitors,
                    "wood": wood,
                    "event_code": event_code,
                    "tournament_results": tournament_results,
                    "manual_overrides": manual_overrides,
                }
            )
            slowest = max(manual_overrides.values())
            output = []
            for record in competitors:
                value = manual_overrides[record.name]
                output.append(
                    SimpleNamespace(
                        name=record.name,
                        mark=3 + round(slowest - value),
                        predicted_time=value,
                        method_used="manual",
                        confidence="VERY HIGH",
                        explanation="internal bridge",
                        std_dev=2.5,
                    )
                )
            return sorted(output, key=lambda item: item.predicted_time, reverse=True)

    adapter._ML_MODEL_CACHE.clear()
    monkeypatch.setattr(adapter, "MLModel", FakeMLModel)
    monkeypatch.setattr(adapter, "get_all_predictions", fake_get_all_predictions)
    monkeypatch.setattr(adapter, "select_best_prediction", fake_select_best_prediction)
    monkeypatch.setattr(adapter, "HandicapCalculator", FakeCalculator)

    results_df = _history_df()
    records = adapter.build_competitor_records(["Alice Axe", "Bob Block"], results_df)
    wood = adapter.build_wood_profile("S01", 300, 5)
    wood_df = pd.DataFrame({"speciesID": ["S01"], "janka_hard": [1690]})

    output = adapter.calculate_handicap_results(
        records,
        wood,
        "SB",
        results_df,
        wood_df=wood_df,
        tournament_results={"Alice Axe": 29.0},
    )

    assert len(calls["train"]) == 1
    assert calls["train"][0][0] is results_df
    assert calls["train"][0][1] is wood_df

    # One prediction pass per competitor: no second pass for the display table.
    assert len(calls["all_predictions"]) == 2
    assert len(calls["select"]) == 2
    assert all(call["ml_model"] is calls["train"][0][2] for call in calls["all_predictions"])
    assert all(call["results_df"] is results_df for call in calls["all_predictions"])
    assert all(call["wood_df"] is wood_df for call in calls["all_predictions"])
    assert all(
        call["llm_client"]["url"] == "http://localhost:11434" for call in calls["all_predictions"]
    )

    bridge_call = calls["calculator"][1]
    assert bridge_call["manual_overrides"] == {
        "Alice Axe": 30.0,
        "Bob Block": 40.0,
    }

    by_name = {row["name"]: row for row in output}
    assert by_name["Alice Axe"]["method_used"] == "ML"
    assert by_name["Alice Axe"]["predictions"]["ml"]["time"] == 30.0
    assert by_name["Bob Block"]["predictions"]["ml"]["time"] == 40.0
    assert by_name["Alice Axe"]["performance_std_dev"] == 2.5
    assert set(by_name["Alice Axe"]["predictions"]) >= {
        "baseline",
        "ml",
        "llm",
    }


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
