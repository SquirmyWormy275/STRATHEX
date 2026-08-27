from __future__ import annotations

from copy import deepcopy

import pytest

from woodchopping.ui import multi_event_ui
from woodchopping.ui.prediction_context import AuthorityStateError, PredictionAuthorityStore


@pytest.fixture
def authority_store(tmp_path):
    return PredictionAuthorityStore(tmp_path / "prediction-authority.db")


def _locked_state(authority_store):
    created = authority_store.create_scope(owner_kind="tournament", scope_id="tournament:abandon-me")
    selected = authority_store.select_engine(
        created.reference,
        engine="v3",
        actor="judge:one",
        selected_at="2026-08-27T16:00:00.000Z",
        reason_code="judge_selection",
        mode="rehearsal",
        contract_identity="strathmark-v3-consumer/5",
        source_identity="strathmark:" + "a" * 40,
    )
    locked = authority_store.lock(
        selected.reference,
        boundary="first_authoritative_numeric_action",
        locked_at="2026-08-27T16:00:01.000Z",
    )
    return {
        "prediction_authority_ref": locked.reference.to_json(),
        "events": [
            {
                "status": "ready",
                "handicap_results_all": [
                    {
                        "competitor_id": "competitor:anon-1",
                        "mark": 3,
                        "engine_version": "3.0.0rc1",
                        "receipt_id": "receipt:one",
                    }
                ],
                "rounds": [],
            }
        ],
    }


def test_loaded_unstarted_state_allows_fresh_selector_without_default(authority_store):
    state = {"tournament_mode": "multi_event", "events": []}

    decision = multi_event_ui.inspect_loaded_prediction_authority(state, authority_store=authority_store)

    assert decision["status"] == "selection_required"
    assert decision["classification"] == "selection_required"
    assert decision["available_actions"] == ("select_engine",)
    assert decision["selector_allowed"] is True
    assert decision["numeric_work_allowed"] is False
    assert "prediction_authority_ref" not in state


def test_loaded_started_state_without_authority_cannot_open_a_fresh_selector(authority_store):
    state = {
        "tournament_mode": "multi_event",
        "events": [{"status": "in_progress", "rounds": []}],
    }

    decision = multi_event_ui.inspect_loaded_prediction_authority(state, authority_store=authority_store)

    assert decision["status"] == "selection_required"
    assert decision["selector_allowed"] is False
    assert decision["read_only"] is True
    assert decision["available_actions"] == ()


def test_proven_legacy_v2_requires_explicit_confirmation(authority_store):
    state = {
        "rounds": [],
        "handicap_results_all": [{"competitor_id": "competitor:anon-1", "mark": 3, "engine_version": "2.0.0"}],
    }
    before = deepcopy(state)

    declined = multi_event_ui.resume_loaded_prediction_authority(
        state,
        authority_store=authority_store,
        actor="judge:one",
        action="confirm_legacy_v2",
        confirmed=False,
        acted_at="2026-08-27T16:10:00.000Z",
    )

    assert declined["status"] == "legacy_v2_confirmation_required"
    assert state == before

    resumed = multi_event_ui.resume_loaded_prediction_authority(
        state,
        authority_store=authority_store,
        actor="judge:one",
        action="confirm_legacy_v2",
        confirmed=True,
        acted_at="2026-08-27T16:10:00.000Z",
    )

    assert resumed["status"] == "ready"
    assert resumed["engine"] == "v2"
    assert resumed["numeric_work_allowed"] is True
    assert state["handicap_results_all"] == before["handicap_results_all"]


def test_reconciliation_required_state_stays_read_only(authority_store):
    state = {
        "handicap_results_all": [
            {"competitor_id": "competitor:anon-1", "mark": 3, "engine_version": "2.0.0"},
            {"competitor_id": "competitor:anon-2", "mark": 7, "engine_version": "3.0.0rc1"},
        ]
    }
    before = deepcopy(state)

    decision = multi_event_ui.resume_loaded_prediction_authority(
        state,
        authority_store=authority_store,
        actor="judge:one",
        action="confirm_legacy_v2",
        confirmed=True,
        acted_at="2026-08-27T16:10:00.000Z",
    )

    assert decision["status"] == "reconciliation_required"
    assert decision["read_only"] is True
    assert decision["available_actions"] == ()
    assert state == before


def test_loaded_unstarted_prompt_requires_explicit_engine_choice(authority_store):
    state = {"tournament_mode": "multi_event", "events": []}
    answers = iter(("y", "1", "restored_save", "confirmed by judge"))

    decision = multi_event_ui.prompt_loaded_prediction_authority(
        state,
        authority_store=authority_store,
        actor="judge:one",
        input_fn=lambda _prompt: next(answers),
    )

    assert decision["status"] == "ready"
    assert decision["engine"] == "v2"
    assert state["prediction_authority_ref"]


def test_loaded_mixed_evidence_prompt_never_opens_selector(authority_store):
    state = {
        "handicap_results_all": [
            {"competitor_id": "competitor:anon-1", "mark": 3, "engine_version": "2.0.0"},
            {"competitor_id": "competitor:anon-2", "mark": 7, "engine_version": "3.0.0rc1"},
        ]
    }

    decision = multi_event_ui.prompt_loaded_prediction_authority(
        state,
        authority_store=authority_store,
        actor="judge:one",
        input_fn=lambda _prompt: pytest.fail("mixed evidence must not prompt for an engine"),
    )

    assert decision["status"] == "reconciliation_required"
    assert decision["read_only"] is True
    assert "prediction_authority_ref" not in state


def test_locked_unissued_scope_requires_confirmation_and_reason_to_abandon(authority_store):
    state = _locked_state(authority_store)
    evidence = deepcopy(state["events"])

    with pytest.raises(ValueError, match="explicit confirmation"):
        multi_event_ui.abandon_locked_prediction_scope(
            state,
            authority_store=authority_store,
            actor="judge:one",
            confirmed=False,
            reason="weather cancellation",
            abandoned_at="2026-08-27T16:20:00.000Z",
        )
    with pytest.raises(ValueError, match="reason"):
        multi_event_ui.abandon_locked_prediction_scope(
            state,
            authority_store=authority_store,
            actor="judge:one",
            confirmed=True,
            reason=" ",
            abandoned_at="2026-08-27T16:20:00.000Z",
        )

    abandoned = multi_event_ui.abandon_locked_prediction_scope(
        state,
        authority_store=authority_store,
        actor="judge:one",
        confirmed=True,
        reason="weather cancellation",
        abandoned_at="2026-08-27T16:20:00.000Z",
    )

    assert abandoned.status == "abandoned"
    assert abandoned.migration_status == "terminal"
    assert abandoned.actor == "judge:one"
    assert abandoned.reason_code == "judge_selection"
    assert abandoned.selected_at == "2026-08-27T16:00:00.000Z"
    assert abandoned.abandoned_by == "judge:one"
    assert abandoned.abandonment_reason == "weather cancellation"
    assert abandoned.abandoned_at == "2026-08-27T16:20:00.000Z"
    assert state["events"] == evidence
    decision = multi_event_ui.inspect_loaded_prediction_authority(state, authority_store=authority_store)
    assert decision["status"] == "terminal"
    assert decision["available_actions"] == ("create_new_scope",)
    assert decision["selector_allowed"] is False
    with pytest.raises(AuthorityStateError, match="closed or abandoned"):
        authority_store.select_engine(
            abandoned.reference,
            engine="v2",
            actor="judge:one",
            selected_at="2026-08-27T16:21:00.000Z",
            reason_code="changed_mind",
            mode="production",
            contract_identity="strathmark-v2/2.0.0",
            source_identity="strathmark:" + "b" * 40,
        )


@pytest.mark.parametrize(
    "issued_or_resulted",
    [
        {"v3_issue_status": "issued", "v3_issue_batches": {"receipt:one": "issue:one"}},
        {"events": [{"status": "in_progress", "rounds": [{"actual_results": {"anon": 31.2}}]}]},
    ],
)
def test_issued_or_resulted_scope_rejects_terminal_abandonment(authority_store, issued_or_resulted):
    state = _locked_state(authority_store)
    for key, value in issued_or_resulted.items():
        state[key] = value
    before = deepcopy(state)

    with pytest.raises(AuthorityStateError, match="issued or resulted"):
        multi_event_ui.abandon_locked_prediction_scope(
            state,
            authority_store=authority_store,
            actor="judge:one",
            confirmed=True,
            reason="operator cancellation",
            abandoned_at="2026-08-27T16:20:00.000Z",
        )

    assert state == before
