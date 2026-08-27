"""Regression coverage for crash-safe tournament-state persistence."""

from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd

from woodchopping.ui import state_persistence
from woodchopping.ui.bracket_ui import (
    generate_bracket_with_byes,
    generate_double_elimination_bracket,
    initialize_bracket_tournament,
)


def _single_state(label: str) -> dict:
    return {
        "event_name": label,
        "all_competitors": ["Alice", "Bob"],
        "all_competitors_df": pd.DataFrame({"competitor_name": ["Alice", "Bob"]}),
        "rounds": [
            {
                "round_name": "Heat 1",
                "round_type": "heat",
                "competitors": ["Alice", "Bob"],
                "competitors_df": pd.DataFrame({"competitor_name": ["Alice", "Bob"]}),
                "status": "pending",
                "advancers": [],
                "finish_order": {},
                "actual_results": {},
            }
        ],
    }


def _multi_state(label: str) -> dict:
    return {
        "tournament_name": label,
        "total_events": 1,
        "events": [
            {
                "event_id": "event-1",
                "event_name": "300mm SB",
                "status": "scheduled",
                "event_type": "handicap",
                "format": "single_heat",
                "all_competitors": ["Alice"],
                "all_competitors_df": pd.DataFrame({"competitor_name": ["Alice"]}),
                "rounds": [
                    {
                        "round_name": "Heat 1",
                        "round_type": "heat",
                        "competitors": ["Alice"],
                        "competitors_df": pd.DataFrame({"competitor_name": ["Alice"]}),
                        "status": "pending",
                        "advancers": [],
                        "finish_order": {},
                        "actual_results": {},
                    }
                ],
            }
        ],
    }


def test_single_state_save_creates_directory_and_rolling_backup(tmp_path):
    target = tmp_path / "nested" / "tournament_state.json"

    assert state_persistence.save_tournament_state(_single_state("first"), str(target))
    assert state_persistence.save_tournament_state(_single_state("second"), str(target))

    assert target.exists()
    backup = Path(str(target) + ".bak")
    assert backup.exists()
    assert json.loads(target.read_text(encoding="utf-8"))["event_name"] == "second"
    assert json.loads(backup.read_text(encoding="utf-8"))["event_name"] == "first"
    assert not list(target.parent.glob("*.tmp"))


def test_single_state_load_recovers_corrupt_primary_from_backup(tmp_path, capsys):
    target = tmp_path / "tournament_state.json"
    assert state_persistence.save_tournament_state(_single_state("first"), str(target))
    assert state_persistence.save_tournament_state(_single_state("second"), str(target))
    target.write_text('{"event_name":', encoding="utf-8")

    loaded = state_persistence.load_tournament_state(str(target))

    assert loaded is not None
    assert loaded["event_name"] == "first"
    assert isinstance(loaded["all_competitors_df"], pd.DataFrame)
    assert json.loads(target.read_text(encoding="utf-8"))["event_name"] == "first"
    assert "Recovered tournament state from backup" in capsys.readouterr().out


def test_single_state_load_recovers_structurally_invalid_primary_from_backup(tmp_path, capsys):
    target = tmp_path / "tournament_state.json"
    assert state_persistence.save_tournament_state(_single_state("first"), str(target))
    assert state_persistence.save_tournament_state(_single_state("second"), str(target))
    invalid = json.loads(target.read_text(encoding="utf-8"))
    invalid["rounds"][0]["status"] = "teleported"
    target.write_text(json.dumps(invalid), encoding="utf-8")

    loaded = state_persistence.load_tournament_state(str(target))

    assert loaded is not None
    assert loaded["event_name"] == "first"
    restored = json.loads(target.read_text(encoding="utf-8"))
    assert restored["event_name"] == "first"
    assert restored["rounds"][0]["status"] == "pending"
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
    assert not state_persistence.save_tournament_state(_single_state("second"), str(target))

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
                        "round_type": "heat",
                        "competitors": ["Alice"],
                        "competitors_df": pd.DataFrame({"competitor_name": ["Alice"]}),
                        "status": "pending",
                        "advancers": [],
                        "finish_order": {},
                        "actual_results": {},
                    }
                ],
                "status": "scheduled",
                "event_type": "handicap",
                "format": "single_heat",
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


def test_multi_state_load_recovers_structurally_invalid_primary_from_backup(tmp_path, capsys):
    target = tmp_path / "multi_tournament_state.json"
    state_persistence.save_multi_event_tournament(_multi_state("first"), str(target))
    state_persistence.save_multi_event_tournament(_multi_state("second"), str(target))
    invalid = json.loads(target.read_text(encoding="utf-8"))
    invalid["events"][0]["rounds"][0]["competitors"] = "Alice"
    target.write_text(json.dumps(invalid), encoding="utf-8")

    loaded = state_persistence.load_multi_event_tournament(str(target))

    assert loaded is not None
    assert loaded["tournament_name"] == "first"
    restored = json.loads(target.read_text(encoding="utf-8"))
    assert restored["tournament_name"] == "first"
    assert restored["events"][0]["rounds"][0]["competitors"] == ["Alice"]
    assert "Recovered tournament state from backup" in capsys.readouterr().out


def test_single_state_rejects_malformed_bracket_match(tmp_path):
    target = tmp_path / "bracket_state.json"
    predictions = {name: {"seed": seed} for seed, name in enumerate(["Alice", "Bob"], 1)}
    state = initialize_bracket_tournament(num_stands=2, tentative_competitors=2)
    state["rounds"] = generate_bracket_with_byes(predictions)
    payload = state_persistence._serialize_single_state(state)
    payload["rounds"][0]["matches"][0]["feeds_from"] = "R0-M1"
    target.write_text(json.dumps(payload), encoding="utf-8")

    assert state_persistence.load_tournament_state(str(target)) is None


def test_generated_single_and_double_elimination_states_round_trip(tmp_path):
    predictions = {name: {"seed": seed} for seed, name in enumerate(["Alice", "Bob", "Carol", "Drew"], 1)}

    single = initialize_bracket_tournament(num_stands=2, tentative_competitors=4)
    single["rounds"] = generate_bracket_with_byes(predictions)
    single_target = tmp_path / "single_bracket.json"
    state_persistence.save_tournament_state(single, str(single_target))

    double = initialize_bracket_tournament(num_stands=2, tentative_competitors=4)
    double.update(generate_double_elimination_bracket(predictions))
    double_target = tmp_path / "double_bracket.json"
    state_persistence.save_tournament_state(double, str(double_target))

    assert state_persistence.load_tournament_state(str(single_target)) is not None
    assert state_persistence.load_tournament_state(str(double_target)) is not None


def test_ui_modules_are_patched_to_atomic_implementations():
    from woodchopping.ui import multi_event_ui, tournament_ui

    state_persistence.install_persistence_guards()

    assert tournament_ui.save_tournament_state is state_persistence.save_tournament_state
    assert tournament_ui.load_tournament_state is state_persistence.load_tournament_state
    assert multi_event_ui.save_multi_event_tournament is state_persistence.save_multi_event_tournament
    assert multi_event_ui.load_multi_event_tournament is state_persistence.load_multi_event_tournament


def test_atomic_state_persists_only_authority_reference_and_resolves_it(tmp_path):
    from woodchopping.ui.prediction_context import PredictionAuthorityStore, attach_authority_reference

    target = tmp_path / "state.json"
    store = PredictionAuthorityStore(tmp_path / "authority.db")
    created = store.create_scope(owner_kind="single_event", scope_id="strathex:atomic-001")
    selected = store.select_engine(
        created.reference,
        engine="v2",
        actor="judge:local",
        selected_at="2026-08-27T15:00:00Z",
        reason_code="known_baseline",
        mode="production",
        contract_identity="v2/2.0.0",
        source_identity="strathmark:a231ad6",
    )
    state = _single_state("authority")
    attach_authority_reference(state, selected.reference)

    assert state_persistence.save_tournament_state(state, str(target), authority_store=store)
    raw = json.loads(target.read_text(encoding="utf-8"))
    assert raw["prediction_authority_ref"] == selected.reference.to_json()
    assert "selected_engine" not in raw
    assert "judge:local" not in target.read_text(encoding="utf-8")

    loaded = state_persistence.load_tournament_state(str(target), authority_store=store)
    assert loaded is not None
    assert loaded["prediction_authority_runtime"]["status"] == "ready"
    assert loaded["prediction_authority_runtime"]["engine"] == "v2"


def test_authority_ahead_of_json_blocks_resume_after_json_save_failure(tmp_path, monkeypatch):
    from woodchopping.ui.prediction_context import PredictionAuthorityStore, attach_authority_reference

    target = tmp_path / "state.json"
    store = PredictionAuthorityStore(tmp_path / "authority.db")
    created = store.create_scope(owner_kind="single_event", scope_id="strathex:atomic-002")
    v2 = store.select_engine(
        created.reference,
        engine="v2",
        actor="judge:local",
        selected_at="2026-08-27T15:00:00Z",
        reason_code="known_baseline",
        mode="production",
        contract_identity="v2/2.0.0",
        source_identity="strathmark:a231ad6",
    )
    state = _single_state("before")
    attach_authority_reference(state, v2.reference)
    assert state_persistence.save_tournament_state(state, str(target), authority_store=store)

    changed = store.select_engine(
        v2.reference,
        engine="v3",
        actor="judge:local",
        selected_at="2026-08-27T15:01:00Z",
        reason_code="evaluation",
        mode="rehearsal",
        contract_identity="v3-consumer/1",
        source_identity="strathmark:abc123",
    )
    attach_authority_reference(state, changed.reference)
    monkeypatch.setattr(
        state_persistence, "_write_temp_file", lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("disk full"))
    )
    assert not state_persistence.save_tournament_state(state, str(target), authority_store=store)

    assert state_persistence.load_tournament_state(str(target), authority_store=store) is None


def test_multi_event_child_authority_override_is_rejected(tmp_path):
    payload = _multi_state("override")
    payload["prediction_authority_ref"] = {
        "authority_store_id": "store-1",
        "scope_id": "strathex:root",
        "revision": 1,
        "digest": "a" * 64,
        "save_id": "save-1",
    }
    payload["events"][0]["prediction_authority_ref"] = dict(payload["prediction_authority_ref"])

    assert not state_persistence.save_multi_event_tournament(payload, str(tmp_path / "multi.json"))


def test_copied_save_requires_explicit_authority_reconciliation(tmp_path):
    from woodchopping.ui.prediction_context import PredictionAuthorityStore, attach_authority_reference

    original = tmp_path / "original.json"
    copied = tmp_path / "copied.json"
    store = PredictionAuthorityStore(tmp_path / "authority.db")
    created = store.create_scope(owner_kind="single_event", scope_id="strathex:copy-001")
    selected = store.select_engine(
        created.reference,
        engine="v2",
        actor="judge:local",
        selected_at="2026-08-27T15:00:00Z",
        reason_code="known_baseline",
        mode="production",
        contract_identity="v2/2.0.0",
        source_identity="strathmark:a231ad6",
    )
    state = _single_state("copy")
    attach_authority_reference(state, selected.reference)
    assert state_persistence.save_tournament_state(state, str(original), authority_store=store)
    copied.write_bytes(original.read_bytes())

    assert state_persistence.load_tournament_state(str(copied), authority_store=store) is None
