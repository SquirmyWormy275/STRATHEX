"""Regression coverage for crash-safe tournament-state persistence."""

from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

from woodchopping.ui import state_persistence


def _single_state(label: str) -> dict:
    return {
        "event_name": label,
        "all_competitors": ["Alice", "Bob"],
        "all_competitors_df": pd.DataFrame({"competitor_name": ["Alice", "Bob"]}),
        "rounds": [
            {
                "round_name": "Heat 1",
                "competitors_df": pd.DataFrame({"competitor_name": ["Alice", "Bob"]}),
            }
        ],
    }


def test_single_state_save_creates_directory_and_rolling_backup(tmp_path):
    target = tmp_path / "nested" / "tournament_state.json"

    state_persistence.save_tournament_state(_single_state("first"), str(target))
    state_persistence.save_tournament_state(_single_state("second"), str(target))

    assert target.exists()
    backup = Path(str(target) + ".bak")
    assert backup.exists()
    assert json.loads(target.read_text(encoding="utf-8"))["event_name"] == "second"
    assert json.loads(backup.read_text(encoding="utf-8"))["event_name"] == "first"
    assert not list(target.parent.glob("*.tmp"))


def test_single_state_load_recovers_corrupt_primary_from_backup(tmp_path, capsys):
    target = tmp_path / "tournament_state.json"
    state_persistence.save_tournament_state(_single_state("first"), str(target))
    state_persistence.save_tournament_state(_single_state("second"), str(target))
    target.write_text('{"event_name":', encoding="utf-8")

    loaded = state_persistence.load_tournament_state(str(target))

    assert loaded is not None
    assert loaded["event_name"] == "first"
    assert isinstance(loaded["all_competitors_df"], pd.DataFrame)
    assert json.loads(target.read_text(encoding="utf-8"))["event_name"] == "first"
    assert "Recovered tournament state from backup" in capsys.readouterr().out


def test_failed_final_replace_preserves_previous_primary(tmp_path, monkeypatch):
    target = tmp_path / "tournament_state.json"
    state_persistence.save_tournament_state(_single_state("first"), str(target))
    original_bytes = target.read_bytes()
    real_replace = os.replace

    def fail_target_replace(source, destination):
        if Path(destination) == target:
            raise OSError("simulated interrupted replacement")
        return real_replace(source, destination)

    monkeypatch.setattr(state_persistence.os, "replace", fail_target_replace)
    state_persistence.save_tournament_state(_single_state("second"), str(target))

    assert target.read_bytes() == original_bytes
    assert not list(tmp_path.glob("*.tmp"))


def test_invalid_primary_and_backup_fail_closed(tmp_path):
    target = tmp_path / "tournament_state.json"
    target.write_text("not-json", encoding="utf-8")
    Path(str(target) + ".bak").write_text("also-not-json", encoding="utf-8")

    assert state_persistence.load_tournament_state(str(target)) is None
    assert target.read_text(encoding="utf-8") == "not-json"


def test_single_state_rejects_malformed_nested_round(tmp_path):
    target = tmp_path / "tournament_state.json"
    target.write_text(
        json.dumps({"all_competitors": [], "all_competitors_df": [], "rounds": ["not-a-round"]}),
        encoding="utf-8",
    )

    assert state_persistence.load_tournament_state(str(target)) is None


def test_multi_state_rejects_malformed_nested_event(tmp_path):
    target = tmp_path / "multi_tournament_state.json"
    target.write_text(json.dumps({"events": [{"rounds": "not-a-list"}]}), encoding="utf-8")

    assert state_persistence.load_multi_event_tournament(str(target)) is None


def test_multi_event_state_round_trip_handles_dataframes_and_numpy(tmp_path):
    target = tmp_path / "multi_tournament_state.json"
    state = {
        "tournament_name": "Spring Open",
        "total_events": np.int64(1),
        "events": [
            {
                "event_name": "300mm SB",
                "all_competitors": ["Alice"],
                "all_competitors_df": pd.DataFrame({"competitor_name": ["Alice"]}),
                "rounds": [
                    {
                        "round_name": "Heat 1",
                        "competitors_df": pd.DataFrame({"competitor_name": ["Alice"]}),
                    }
                ],
            }
        ],
        "competitor_roster_df": pd.DataFrame({"competitor_name": ["Alice"]}),
    }

    state_persistence.save_multi_event_tournament(state, str(target))
    loaded = state_persistence.load_multi_event_tournament(str(target))

    assert loaded is not None
    assert loaded["total_events"] == 1
    assert isinstance(loaded["competitor_roster_df"], pd.DataFrame)
    assert isinstance(loaded["events"][0]["all_competitors_df"], pd.DataFrame)
    assert isinstance(loaded["events"][0]["rounds"][0]["competitors_df"], pd.DataFrame)
    assert loaded["events"][0]["event_type"] == "handicap"


def test_ui_modules_are_patched_to_atomic_implementations():
    from woodchopping.ui import multi_event_ui, tournament_ui

    state_persistence.install_persistence_guards()

    assert tournament_ui.save_tournament_state is state_persistence.save_tournament_state
    assert tournament_ui.load_tournament_state is state_persistence.load_tournament_state
    assert multi_event_ui.save_multi_event_tournament is state_persistence.save_multi_event_tournament
    assert multi_event_ui.load_multi_event_tournament is state_persistence.load_multi_event_tournament
