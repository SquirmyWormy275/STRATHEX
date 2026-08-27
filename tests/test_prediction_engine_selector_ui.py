from __future__ import annotations

import re
from datetime import datetime, timezone

import pytest

import explanation_system_functions as explanations
from woodchopping.ui import multi_event_ui
from woodchopping.ui.prediction_context import PredictionAuthorityStore


@pytest.fixture
def authority_store(tmp_path):
    return PredictionAuthorityStore(tmp_path / "prediction-authority.db")


def _v3_status(status: str = "production_ready") -> dict[str, str]:
    return {
        "status": status,
        "contract_identity": "strathmark-v3-consumer/1",
        "source_identity": "strathmark:abc123",
        "message": "Local V3 service passed its configured readiness check.",
    }


def test_selector_has_no_default_and_records_deliberate_v2_choice(authority_store, monkeypatch, capsys):
    answers = iter(["", "1", "known_baseline", "Trusted baseline for this event"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(answers))

    state: dict = {}
    receipt = multi_event_ui.select_prediction_engine_for_scope(
        state,
        authority_store=authority_store,
        owner_kind="single_event",
        readiness_provider=lambda: _v3_status("ineligible"),
        actor="judge-7",
        selected_at="2026-08-27T08:30:00Z",
    )

    assert receipt.engine == "v2"
    assert receipt.mode == "production"
    assert receipt.reason_code == "known_baseline"
    assert receipt.reason_note == "Trusted baseline for this event"
    assert receipt.contract_identity == "strathmark-v2/2.0.0"
    assert receipt.source_identity == "strathmark:a231ad65fe82317516cc82a282761d73adb0c0e3"
    assert set(state) == {"prediction_authority_ref"}
    assert "No engine is selected by default" in capsys.readouterr().out


def test_selector_rejects_reason_that_cannot_enter_strathmark_contract(authority_store, monkeypatch, capsys):
    answers = iter(["1", "Changed because maybe", "1", "valid_reason", ""])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(answers))

    receipt = multi_event_ui.select_prediction_engine_for_scope(
        {},
        authority_store=authority_store,
        owner_kind="single_event",
        actor="judge-7",
        selected_at="2026-08-27T08:30:00.000Z",
    )

    assert receipt.reason_code == "valid_reason"
    assert "lowercase reason code" in capsys.readouterr().out


def test_default_selection_timestamp_uses_v3_utc_millisecond_shape(authority_store, monkeypatch):
    answers = iter(["1", "known_baseline", ""])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(answers))

    receipt = multi_event_ui.select_prediction_engine_for_scope(
        {},
        authority_store=authority_store,
        owner_kind="single_event",
        actor="judge-7",
    )

    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z", receipt.selected_at)


def test_v3_status_failure_can_be_retried_before_rehearsal_selection(authority_store, monkeypatch, capsys):
    statuses = iter([_v3_status("status_failed"), _v3_status("rehearsal_ready")])
    answers = iter(["r", "2", "evaluation", "Compare with V2 after the show"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(answers))

    state: dict = {}
    receipt = multi_event_ui.select_prediction_engine_for_scope(
        state,
        authority_store=authority_store,
        owner_kind="tournament",
        readiness_provider=lambda: next(statuses),
        actor="judge-7",
        selected_at="2026-08-27T08:31:00Z",
    )

    assert receipt.engine == "v3"
    assert receipt.mode == "rehearsal"
    assert receipt.contract_identity == "strathmark-v3-consumer/1"
    output = capsys.readouterr().out
    assert "STATUS CHECK FAILED" in output
    assert "REHEARSAL READY" in output
    assert "does not claim production readiness" in output


def test_v3_readiness_exception_is_rendered_as_failed_and_v2_remains_selectable(authority_store, monkeypatch, capsys):
    def failed_check():
        raise ConnectionError("service unavailable")

    answers = iter(["1", "service_unavailable", "Proceed with established V2"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(answers))
    state: dict = {}

    receipt = multi_event_ui.select_prediction_engine_for_scope(
        state,
        authority_store=authority_store,
        owner_kind="single_event",
        readiness_provider=failed_check,
        actor="judge-7",
        selected_at="2026-08-27T08:31:30Z",
    )

    assert receipt.engine == "v2"
    output = capsys.readouterr().out
    assert "STATUS CHECK FAILED" in output
    assert "service unavailable" in output


@pytest.mark.parametrize(
    ("status", "label"),
    [
        ("checking", "CHECKING"),
        ("production_ready", "PRODUCTION READY"),
        ("rehearsal_ready", "REHEARSAL READY"),
        ("ineligible", "INELIGIBLE"),
        ("status_failed", "STATUS CHECK FAILED"),
    ],
)
def test_all_v3_readiness_states_are_rendered_without_overclaiming(status, label):
    rendered = multi_event_ui.format_v3_readiness(_v3_status(status))

    assert label in rendered
    if status != "production_ready":
        assert "production-ready" not in rendered.lower()


def test_tournament_creation_selects_once_and_children_only_inherit(authority_store, monkeypatch, capsys):
    answers = iter(["Spring Open", "2026-08-27", "1", "judge_selection", "Tournament-wide choice"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(answers))

    state = multi_event_ui.create_multi_event_tournament(
        authority_store=authority_store,
        readiness_provider=lambda: _v3_status("production_ready"),
        actor="judge-7",
        selected_at="2026-08-27T08:32:00Z",
    )

    receipt = multi_event_ui.resolve_prediction_engine(state, authority_store)
    assert receipt.owner_kind == "tournament"
    assert receipt.engine == "v2"
    assert state["events"] == []

    multi_event_ui.display_inherited_prediction_engine(state, authority_store)
    output = capsys.readouterr().out
    assert "inherited by every event and round" in output
    assert "cannot be changed per event" in output


def test_engine_banner_is_compact_persistent_and_championship_safe(authority_store, monkeypatch, capsys):
    answers = iter(["1", "judge_selection", ""])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(answers))
    state: dict = {}
    multi_event_ui.select_prediction_engine_for_scope(
        state,
        authority_store=authority_store,
        owner_kind="single_event",
        readiness_provider=lambda: _v3_status(),
        actor="judge-7",
        selected_at=datetime.now(timezone.utc).isoformat(),
    )

    multi_event_ui.display_prediction_engine_banner(state, authority_store)
    output = capsys.readouterr().out
    assert "PREDICTION ENGINE: V2 | MODE: PRODUCTION | UNLOCKED" in output
    assert "Championship and bracket Mark 3 rules remain unchanged" in output


def test_engine_help_explains_scope_lock_modes_and_no_fallback(capsys):
    explanations.show_prediction_engine_help(pause=False)
    output = capsys.readouterr().out

    assert "single event" in output.lower()
    assert "tournament creation" in output.lower()
    assert "inherit" in output.lower()
    assert "no silent fallback" in output.lower()
    assert "rehearsal" in output.lower()
    assert "mark 3" in output.lower()
