"""Ensure every live prediction surface is routed through STRATHMARK v2."""

from datetime import date

import pandas as pd
import pytest

import woodchopping.data as data
import woodchopping.handicaps as handicaps
import woodchopping.ui.championship_simulator as championship_simulator
import woodchopping.ui.multi_event_ui as multi_event_ui
import woodchopping.ui.schedule_printout as schedule_printout
import woodchopping.ui.tournament_ui as tournament_ui
from woodchopping.ui.bracket_ui import generate_bracket_seeds
from woodchopping.ui.prediction_display import (
    display_basic_prediction_table,
    display_comprehensive_prediction_analysis,
)


def test_bracket_seeding_uses_one_v2_field_calculation(monkeypatch):
    calls = []

    def fake_calculate(competitors_df, species, diameter, quality, event_code, results_df, **kwargs):
        calls.append(
            {
                "competitors_df": competitors_df,
                "species": species,
                "diameter": diameter,
                "quality": quality,
                "event_code": event_code,
                "results_df": results_df,
                **kwargs,
            }
        )
        return [
            {
                "name": "Bob Block",
                "predicted_time": 40.0,
                "method_used": "V2 Core",
                "confidence": "HIGH",
                "explanation": "v2",
                "predictions": {"v2": {"time": 40.0}},
                "engine_version": "2.0.0",
            },
            {
                "name": "Alice Axe",
                "predicted_time": 30.0,
                "method_used": "V2 Core",
                "confidence": "HIGH",
                "explanation": "v2",
                "predictions": {"v2": {"time": 30.0}},
                "engine_version": "2.0.0",
            },
        ]

    monkeypatch.setattr(handicaps, "calculate_ai_enhanced_handicaps", fake_calculate)
    monkeypatch.setattr(data, "load_results_df", lambda: pd.DataFrame())
    competitors = pd.DataFrame(
        {
            "competitor_id": ["C001", "C002"],
            "competitor_name": ["Alice Axe", "Bob Block"],
        }
    )

    predictions = generate_bracket_seeds(
        competitors,
        "S01",
        300,
        5,
        "SB",
        prediction_as_of=date(2026, 8, 18),
    )

    assert len(calls) == 1
    assert calls[0]["prediction_as_of"] == date(2026, 8, 18)
    assert predictions["Alice Axe"]["seed"] == 1
    assert predictions["Bob Block"]["seed"] == 2
    assert predictions["Alice Axe"]["engine_version"] == "2.0.0"


def test_v2_prediction_tables_surface_operator_evidence_in_ascii(capsys):
    results = [
        {
            "name": "Alice Axe",
            "mark": 3,
            "predicted_time": 31.25,
            "prediction_interval": {"lower": 27.0, "upper": 36.0},
            "performance_std_dev": 2.5,
            "confidence": "HIGH",
            "method_used": "V2 Core",
            "engine_version": "2.0.0",
            "evidence_cutoff": "2026-08-18",
            "optimizer": "posterior_crn_v2",
            "warnings": ["one undated result excluded"],
            "ignored_factors": ["wood_quality"],
            "degraded": True,
        }
    ]
    wood = {"event": "SB"}

    display_basic_prediction_table(results, wood)
    display_comprehensive_prediction_analysis(results, wood)
    output = capsys.readouterr().out

    assert output.isascii()
    assert "27.0-36.0s" in output
    assert "DEGRADED" in output
    assert "one undated result excluded" in output
    assert "2026-08-18" in output
    assert "posterior_crn_v2" in output
    assert "wood_quality" in output


def test_advancing_field_calculation_failure_does_not_generate_partial_round(monkeypatch, capsys):
    monkeypatch.setattr(data, "load_results_df", lambda: pd.DataFrame())
    monkeypatch.setattr(handicaps, "calculate_ai_enhanced_handicaps", lambda *args, **kwargs: None)
    roster = pd.DataFrame(
        {
            "competitor_id": ["C001", "C002"],
            "competitor_name": ["Alice Axe", "Bob Block"],
        }
    )
    state = {
        "all_competitors_df": roster,
        "rounds": [],
        "num_stands": 2,
        "wood_species": "S01",
        "wood_diameter": 300,
        "wood_quality": 5,
        "event_code": "SB",
        "prediction_as_of": "2026-08-18",
    }

    assert tournament_ui.generate_next_round(state, roster["competitor_name"].tolist(), "final") == []
    assert state["rounds"] == []
    assert "No next round was generated" in capsys.readouterr().out


def test_championship_prediction_failure_aborts_the_whole_field(monkeypatch, capsys):
    calls = []

    def fail_calculation(*args, **kwargs):
        calls.append((args, kwargs))
        return None

    monkeypatch.setattr(championship_simulator, "calculate_ai_enhanced_handicaps", fail_calculation)
    roster = pd.DataFrame(
        {
            "competitor_id": ["C001", "C002"],
            "competitor_name": ["Alice Axe", "Bob Block"],
        }
    )
    wood = {"species": "S01", "size_mm": 300, "quality": 5, "event": "SB"}

    predictions = championship_simulator._generate_championship_predictions(
        roster,
        wood,
        {name: wood for name in roster["competitor_name"]},
        results_df=pd.DataFrame(),
        prediction_as_of=date(2026, 8, 18),
    )

    assert predictions == []
    assert len(calls) == 1
    assert "complete championship field" in capsys.readouterr().out


def test_championship_common_wood_uses_one_field_calculation(monkeypatch):
    calls = []

    def calculate(group_df, *args, **kwargs):
        calls.append((group_df.copy(), args, kwargs))
        return [
            {
                "name": name,
                "predicted_time": 30.0 + index,
                "engine_version": "2.0.0",
                "model_version": "model-1",
                "calibration_version": "calibration-1",
                "evidence_cutoff": "2026-08-18",
            }
            for index, name in enumerate(group_df["competitor_name"])
        ]

    monkeypatch.setattr(championship_simulator, "calculate_ai_enhanced_handicaps", calculate)
    roster = pd.DataFrame(
        {
            "competitor_id": ["C001", "C002"],
            "competitor_name": ["Alice Axe", "Bob Block"],
        }
    )
    wood = {"species": "S01", "size_mm": 300, "quality": 5, "event": "SB"}

    predictions = championship_simulator._generate_championship_predictions(
        roster,
        wood,
        {name: wood for name in roster["competitor_name"]},
        results_df=pd.DataFrame(),
        prediction_as_of=date(2026, 8, 18),
    )

    assert len(calls) == 1
    assert calls[0][0]["competitor_name"].tolist() == ["Alice Axe", "Bob Block"]
    assert [prediction["name"] for prediction in predictions] == ["Alice Axe", "Bob Block"]


def test_championship_rejects_mixed_model_snapshots(monkeypatch, capsys):
    call_count = 0

    def calculate(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        name = args[0].iloc[0]["competitor_name"]
        return [
            {
                "name": name,
                "predicted_time": 30.0 + call_count,
                "engine_version": "2.0.0",
                "model_version": f"model-{call_count}",
                "calibration_version": "calibration-1",
                "evidence_cutoff": "2026-08-18",
            }
        ]

    monkeypatch.setattr(championship_simulator, "calculate_ai_enhanced_handicaps", calculate)
    roster = pd.DataFrame(
        {
            "competitor_id": ["C001", "C002"],
            "competitor_name": ["Alice Axe", "Bob Block"],
        }
    )
    wood = {"species": "S01", "size_mm": 300, "quality": 5, "event": "SB"}
    bob_wood = {"species": "S02", "size_mm": 300, "quality": 5, "event": "SB"}

    predictions = championship_simulator._generate_championship_predictions(
        roster,
        wood,
        {"Alice Axe": wood, "Bob Block": bob_wood},
        results_df=pd.DataFrame(),
        prediction_as_of=date(2026, 8, 18),
    )

    assert predictions == []
    assert call_count == 2
    assert "rather than mixing model snapshots" in capsys.readouterr().out


def test_championship_simulation_count_is_memory_bounded():
    assert championship_simulator._championship_simulation_count(8) == 250_000
    assert championship_simulator._championship_simulation_count(64) == 31_250
    assert championship_simulator._championship_simulation_count(0) == 0


def test_failed_multi_event_recalculation_clears_stale_ready_marks(monkeypatch, capsys):
    stale_marks = [{"name": "Alice Axe", "mark": 99, "predicted_time": 30.0}]
    roster = pd.DataFrame({"competitor_id": ["C001"], "competitor_name": ["Alice Axe"]})
    event = {
        "event_name": "Stale Event",
        "event_type": "handicap",
        "event_code": "SB",
        "wood_species": "S01",
        "wood_diameter": 300,
        "wood_quality": 5,
        "all_competitors": ["Alice Axe"],
        "all_competitors_df": roster,
        "handicap_results_all": stale_marks,
        "status": "ready",
    }
    state = {"tournament_date": "2026-08-18", "events": [event]}
    answers = iter(["y", ""])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(answers))
    monkeypatch.setattr(multi_event_ui, "auto_save_multi_event", lambda _state: True)
    monkeypatch.setattr(multi_event_ui, "calculate_ai_enhanced_handicaps", lambda *args, **kwargs: None)

    result = multi_event_ui.calculate_all_event_handicaps(state, pd.DataFrame())

    assert result is state
    assert event["handicap_results_all"] == []
    assert event["status"] == "recalculation_failed"
    assert "NOT READY" in capsys.readouterr().out


def test_failed_scheduled_recalculation_invalidates_rounds_and_export(monkeypatch, capsys):
    stale_marks = [{"name": "Alice Axe", "mark": 99, "predicted_time": 30.0}]
    roster = pd.DataFrame({"competitor_id": ["C001"], "competitor_name": ["Alice Axe"]})
    event = {
        "event_name": "Scheduled Event",
        "event_type": "handicap",
        "event_code": "SB",
        "wood_species": "S01",
        "wood_diameter": 300,
        "wood_quality": 5,
        "all_competitors": ["Alice Axe"],
        "all_competitors_df": roster,
        "handicap_results_all": stale_marks,
        "status": "scheduled",
        "rounds": [
            {
                "round_name": "Heat 1",
                "status": "pending",
                "competitors": ["Alice Axe"],
                "handicap_results": stale_marks,
            }
        ],
    }
    state = {
        "tournament_mode": "multi_event",
        "tournament_date": "2026-08-18",
        "events": [event],
        "schedule": ["stale export row"],
    }
    answers = iter(["y", ""])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(answers))
    monkeypatch.setattr(multi_event_ui, "auto_save_multi_event", lambda _state: True)
    monkeypatch.setattr(multi_event_ui, "calculate_ai_enhanced_handicaps", lambda *args, **kwargs: None)

    multi_event_ui.calculate_all_event_handicaps(state, pd.DataFrame())

    assert event["handicap_results_all"] == []
    assert event["rounds"] == []
    assert event["status"] == "recalculation_failed"
    assert state["schedule"] == []
    with pytest.raises(ValueError, match="Cannot export a schedule"):
        schedule_printout.generate_printable_schedule(state)
    assert "generated heats will be cleared" in capsys.readouterr().out


def test_multi_event_recalculation_is_blocked_after_results_begin(monkeypatch, capsys):
    event = {
        "event_name": "Started Event",
        "event_type": "handicap",
        "handicap_results_all": [{"name": "Alice Axe", "mark": 3}],
        "status": "in_progress",
        "rounds": [{"status": "in_progress", "actual_results": {"Alice Axe": 29.1}}],
    }
    state = {"events": [event]}
    monkeypatch.setattr("builtins.input", lambda _prompt="": "")
    monkeypatch.setattr(
        multi_event_ui,
        "calculate_ai_enhanced_handicaps",
        lambda *args, **kwargs: pytest.fail("calculation must not run"),
    )

    assert multi_event_ui.calculate_all_event_handicaps(state, pd.DataFrame()) is state
    assert event["status"] == "in_progress"
    assert event["rounds"][0]["actual_results"] == {"Alice Axe": 29.1}
    assert "cannot be recalculated after competition has begun" in capsys.readouterr().out


def test_results_entry_rejects_failed_recalculation(monkeypatch, capsys):
    event = {
        "event_name": "Failed Event",
        "event_type": "handicap",
        "status": "recalculation_failed",
        "rounds": [],
    }
    state = {"events": [event]}
    monkeypatch.setattr("builtins.input", lambda _prompt="": "")
    monkeypatch.setattr(
        multi_event_ui,
        "append_results_to_excel",
        lambda *args, **kwargs: pytest.fail("result writer must not run"),
    )

    assert multi_event_ui.sequential_results_workflow(state, {}, pd.DataFrame()) is state
    assert "not ready for results" in capsys.readouterr().out
