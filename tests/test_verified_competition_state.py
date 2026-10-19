"""Exact local save authenticity and multi-event judge approval boundaries."""

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from woodchopping.ui import multi_event_ui, state_persistence
from woodchopping.ui.official_eligibility import require_official_eligibility
from woodchopping.ui.prediction_context import PredictionAuthorityStore, attach_authority_reference
from woodchopping.ui.workflow_integrity import approve_marks, bind_calculation


@pytest.fixture
def selected_state(tmp_path, monkeypatch):
    store = PredictionAuthorityStore(tmp_path / "authority.db")
    monkeypatch.setattr(multi_event_ui, "_prediction_authority_store", store)
    scope = store.create_scope(owner_kind="tournament")
    selected = store.select_engine(
        scope.reference,
        engine="v2",
        actor="judge",
        selected_at="2026-10-19T00:00:00Z",
        reason_code="known_baseline",
        mode="production",
        contract_identity="strathmark-v2/2.0.0",
        source_identity="strathmark:f064d67abe4baf7672239a14796c0bdc4f8c2071",
    )
    rows = [{"name": "Alice", "mark": 3, "predicted_time": 20.0}, {"name": "Bob", "mark": 15, "predicted_time": 8.0}]
    event = {
        "event_id": "event-1",
        "event_name": "Synthetic",
        "event_type": "handicap",
        "format": "single_heat",
        "all_competitors": ["Alice", "Bob"],
        "num_stands": 2,
        "all_competitors_df": pd.DataFrame({"competitor_name": ["Alice", "Bob"]}),
        "wood_species": "Aspen",
        "wood_diameter": 300,
        "wood_quality": 7,
        "event_code": "SB",
        "status": "ready",
        "handicap_results_all": rows,
        "rounds": [],
    }
    state = {"tournament_mode": "multi_event", "events": [event]}
    attach_authority_reference(state, selected.reference)
    bind_calculation(event, state)
    return store, state, event


def test_current_but_unapproved_multi_event_cannot_generate_or_record(selected_state, monkeypatch):
    store, state, event = selected_state
    monkeypatch.setattr("builtins.input", lambda *_: pytest.fail("unapproved event reached interaction"))
    with pytest.raises(ValueError, match="approve"):
        require_official_eligibility(state, authority_store=store)
    multi_event_ui.generate_complete_day_schedule(state, authority_store=store)
    multi_event_ui.sequential_results_workflow(state, {}, pd.DataFrame(), authority_store=store)
    assert event["rounds"] == []


def test_exact_approval_allows_schedule_but_mutation_blocks_results(selected_state, monkeypatch):
    store, state, event = selected_state
    approve_marks(event, "JD", "2026-10-19T00:00:00Z", root_state=state)
    monkeypatch.setattr("builtins.input", lambda *_: "")
    monkeypatch.setattr(multi_event_ui, "auto_save_multi_event", lambda *a, **k: True)
    multi_event_ui.generate_complete_day_schedule(state, authority_store=store)
    assert event["status"] == "scheduled"
    require_official_eligibility(state, authority_store=store)
    event["handicap_results_all"][0]["mark"] = 99
    with pytest.raises(ValueError, match="approve"):
        require_official_eligibility(state, authority_store=store)


def test_actual_approval_menu_binds_exact_sheet(selected_state, monkeypatch):
    store, state, event = selected_state
    answers = iter(["1", "1", "", "3"])
    monkeypatch.setattr("builtins.input", lambda *_: next(answers))
    monkeypatch.setattr("woodchopping.ui.handicap_ui.judge_approval", lambda: ("JD", "2026-10-19T00:00:00Z"))
    monkeypatch.setattr(multi_event_ui, "auto_save_multi_event", lambda *a, **k: True)
    multi_event_ui.approve_event_handicaps(state)
    assert event["mark_approval"]["judge"] == "JD"
    require_official_eligibility(state, authority_store=store)


def test_local_save_roundtrip_authenticates_exact_bytes(selected_state, tmp_path):
    store, state, _ = selected_state
    target = tmp_path / "competition.json"
    assert state_persistence.save_multi_event_tournament(state, str(target), authority_store=store)
    first = target.read_bytes()
    loaded = state_persistence.load_multi_event_tournament(str(target), authority_store=store)
    assert loaded is not None
    loaded["tournament_name"] = "Updated"
    assert state_persistence.save_multi_event_tournament(loaded, str(target), authority_store=store)
    assert Path(str(target) + ".bak").read_bytes() == first
    current, previous = store.save_payload_digests(target)
    assert current == hashlib.sha256(target.read_bytes()).hexdigest()
    assert previous == hashlib.sha256(first).hexdigest()


@pytest.mark.parametrize("mutation", ["results", "rollback", "copy", "remove"])
def test_changed_or_relocated_save_never_activates_or_promotes_backup(selected_state, tmp_path, mutation, capsys):
    store, state, _ = selected_state
    target = tmp_path / "competition.json"
    assert state_persistence.save_multi_event_tournament(state, str(target), authority_store=store)
    first = target.read_bytes()
    state["tournament_name"] = "Current"
    assert state_persistence.save_multi_event_tournament(state, str(target), authority_store=store)
    if mutation == "copy":
        copied = tmp_path / "copied.json"
        copied.write_bytes(target.read_bytes())
        target = copied
    elif mutation == "rollback":
        target.write_bytes(first)
    elif mutation == "remove":
        target.unlink()
    else:
        payload = json.loads(target.read_bytes())
        payload["events"][0]["final_results"] = {"first_place": "Mallory"}
        target.write_text(json.dumps(payload))
    before = target.read_bytes() if target.exists() else None
    assert state_persistence.load_multi_event_tournament(str(target), authority_store=store) is None
    assert (target.read_bytes() if target.exists() else None) == before
    assert "retained unchanged" in capsys.readouterr().out


def test_unbound_historical_completed_save_preserved_and_not_overwritten(selected_state, tmp_path):
    store, state, _ = selected_state
    target = tmp_path / "historical.json"
    payload = state_persistence._serialize_multi_state(state)
    payload.pop("prediction_authority_ref")
    payload["events"][0]["status"] = "completed"
    payload["events"][0]["final_results"] = {"first_place": "Mallory"}
    target.write_text(json.dumps(payload))
    original = target.read_bytes()
    assert state_persistence.load_multi_event_tournament(str(target), authority_store=store) is None
    assert not state_persistence.save_multi_event_tournament(state, str(target), authority_store=store)
    assert target.read_bytes() == original
    assert store.save_payload_digests(target) == (None, None)


@pytest.mark.parametrize(
    "field,value", [("advancers", ["Mallory"]), ("finish_order", {"Mallory": 1}), ("actual_results", {"Mallory": 10.0})]
)
def test_result_identity_cannot_escape_its_declared_field(field, value):
    round_state = {
        "round_name": "Final",
        "round_type": "final",
        "status": "completed",
        "competitors": ["Alice"],
        "competitors_df": [],
        field: value,
    }
    with pytest.raises(ValueError, match="outside this field"):
        state_persistence._validate_regular_round(round_state, "Synthetic")
