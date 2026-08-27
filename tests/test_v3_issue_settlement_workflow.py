"""V3 mark issue and result settlement must be durable and receipt-bound."""

from __future__ import annotations

from copy import deepcopy

import pandas as pd
import pytest

from woodchopping.ui.multi_event_ui import (
    acknowledge_v3_issued_marks,
    record_and_settle_v3_round,
    record_and_settle_v3_single_event,
    review_v3_approval_queue,
)
from woodchopping.ui.prediction_context import PredictionAuthorityStore, attach_authority_reference


def _v3_state(tmp_path):
    store = PredictionAuthorityStore(tmp_path / "authority.db")
    created = store.create_scope(owner_kind="tournament", scope_id="tournament:show")
    selected = store.select_engine(
        created.reference,
        engine="v3",
        actor="actor:judge-one",
        selected_at="2026-08-27T16:00:00.000Z",
        reason_code="judge_selection",
        mode="rehearsal",
        contract_identity="contract:v3",
        source_identity="c" * 40,
    )
    locked = store.lock(
        selected.reference,
        boundary="first_authoritative_numeric_action",
        locked_at="2026-08-27T16:00:01.000Z",
    )
    state = {"events": []}
    attach_authority_reference(state, locked.reference)
    return state, store


def _field_rows():
    return [
        {
            "name": "Alice",
            "competitor_id": "competitor:alice",
            "receipt_id": "receipt:heat-one",
            "receipt_digest": "a" * 64,
            "mark": 3,
            "engine_version": "3.0.0",
        },
        {
            "name": "Bob",
            "competitor_id": "competitor:bob",
            "receipt_id": "receipt:heat-one",
            "receipt_digest": "a" * 64,
            "mark": 8,
            "engine_version": "3.0.0",
        },
    ]


def test_acknowledgment_uses_stable_issue_identity_and_stores_batch_on_field_rows(tmp_path):
    state, store = _v3_state(tmp_path)
    rows = _field_rows()
    event = {"handicap_results_all": rows, "rounds": [{"handicap_results": rows}]}
    state["events"].append(event)
    approval_rows = [{"receipt_id": "receipt:heat-one", "receipt_content_digest": "a" * 64}]

    class Adapter:
        payloads = []

        def acknowledge_issue(self, _context, payload):
            self.payloads.append(payload)
            return {
                "schema_version": "strathmark-v3-issue-acknowledgment-response-v1",
                "issue_batch_id": "issue_batch:one",
                "receipt_ids": ["receipt:heat-one"],
            }

    adapter = Adapter()
    first = acknowledge_v3_issued_marks(
        state,
        approval_rows,
        authority_store=store,
        v3_adapter=adapter,
        issued_at_utc="2026-08-27T16:05:00.000Z",
    )
    second = acknowledge_v3_issued_marks(
        state,
        approval_rows,
        authority_store=store,
        v3_adapter=adapter,
        issued_at_utc="2026-08-27T16:06:00.000Z",
    )

    assert first == second == "issue_batch:one"
    assert len(adapter.payloads) == 1
    assert adapter.payloads[0]["upstream_issue_id"].startswith("issue:")
    assert all(row["issue_batch_id"] == "issue_batch:one" for row in rows)
    assert state["v3_issue_batches"]["receipt:heat-one"] == "issue_batch:one"


def test_accepted_approval_is_acknowledged_before_review_returns(tmp_path):
    state, store = _v3_state(tmp_path)
    rows = _field_rows()
    state["events"].append({"handicap_results_all": rows})
    approval_row = {
        "field_id": "field:heat-one",
        "receipt_id": "receipt:heat-one",
        "receipt_content_digest": "a" * 64,
        "receipt_revision": 1,
        "upstream_field_revision": 1,
        "row_digest": "b" * 64,
        "call_order": 1,
        "decision_state": "undecided",
        "ordinary_batch_eligible": True,
        "degraded_batch_eligible": False,
    }
    pages = iter(
        [
            {"snapshot_id": "approval_snapshot:" + "1" * 64, "rows": [approval_row]},
            {"snapshot_id": "approval_snapshot:" + "2" * 64, "rows": []},
        ]
    )

    class Adapter:
        def approval_page(self, *_args, **_kwargs):
            return next(pages)

        def decide_approval(self, _context, payload):
            return {"action": payload["action"]}

        def acknowledge_issue(self, _context, payload):
            return {
                "issue_batch_id": "issue_batch:accepted",
                "receipt_ids": [item["receipt_id"] for item in payload["receipt_bindings"]],
            }

    decisions = review_v3_approval_queue(
        state,
        authority_store=store,
        v3_adapter=Adapter(),
        input_fn=lambda _prompt: "y",
        checkpoint_callback=lambda _state: True,
    )

    assert decisions == [{"action": "ordinary_batch_accept"}]
    assert state["v3_issue_status"] == "issued"
    assert rows[0]["issue_batch_id"] == "issue_batch:accepted"


def test_approval_does_not_reach_strathmark_until_pending_decision_is_checkpointed(tmp_path):
    state, store = _v3_state(tmp_path)
    approval_row = {
        "field_id": "field:heat-one",
        "receipt_id": "receipt:heat-one",
        "receipt_content_digest": "a" * 64,
        "receipt_revision": 1,
        "upstream_field_revision": 1,
        "row_digest": "b" * 64,
        "call_order": 1,
        "decision_state": "undecided",
        "ordinary_batch_eligible": True,
        "degraded_batch_eligible": False,
    }

    class Adapter:
        def approval_page(self, *_args, **_kwargs):
            return {"snapshot_id": "approval_snapshot:" + "1" * 64, "rows": [approval_row]}

        def decide_approval(self, _context, _payload):
            raise AssertionError("decision must not be sent before its recovery payload is durable")

    with pytest.raises(RuntimeError, match="pending V3 approval decision"):
        review_v3_approval_queue(
            state,
            authority_store=store,
            v3_adapter=Adapter(),
            input_fn=lambda _prompt: "y",
            checkpoint_callback=lambda _state: False,
        )

    assert state["v3_pending_approval_decision"]["action"] == "ordinary_batch_accept"


def test_review_reentry_retries_pending_issue_without_redeciding_or_changing_payload(tmp_path):
    from woodchopping.strathmark_v3_client import V3ClientError

    state, store = _v3_state(tmp_path)
    rows = _field_rows()
    state["events"].append({"handicap_results_all": rows})
    approval_row = {
        "field_id": "field:heat-one",
        "receipt_id": "receipt:heat-one",
        "receipt_content_digest": "a" * 64,
        "receipt_revision": 1,
        "upstream_field_revision": 1,
        "row_digest": "b" * 64,
        "call_order": 1,
        "decision_state": "undecided",
        "ordinary_batch_eligible": True,
        "degraded_batch_eligible": False,
    }
    pages = iter(
        [
            {"snapshot_id": "approval_snapshot:" + "1" * 64, "rows": [approval_row]},
            {"snapshot_id": "approval_snapshot:" + "2" * 64, "rows": []},
        ]
    )

    class Adapter:
        decisions = 0
        issue_payloads = []

        def approval_page(self, *_args, **_kwargs):
            return next(pages)

        def decide_approval(self, _context, payload):
            self.decisions += 1
            return {"action": payload["action"]}

        def acknowledge_issue(self, _context, payload):
            self.issue_payloads.append(payload)
            if len(self.issue_payloads) == 1:
                raise V3ClientError("blocked after approval")
            return {
                "issue_batch_id": "issue_batch:recovered",
                "receipt_ids": ["receipt:heat-one"],
            }

    adapter = Adapter()
    assert review_v3_approval_queue(
        state,
        authority_store=store,
        v3_adapter=adapter,
        input_fn=lambda _prompt: "y",
        checkpoint_callback=lambda _state: True,
    ) == [{"action": "ordinary_batch_accept"}]
    assert state["v3_issue_status"] == "accepted_unacknowledged"
    assert state["v3_pending_issue_acknowledgments"]

    assert review_v3_approval_queue(
        state,
        authority_store=store,
        v3_adapter=adapter,
        input_fn=lambda _prompt: "y",
        checkpoint_callback=lambda _state: True,
    ) == [{"action": "ordinary_batch_accept"}]
    assert adapter.decisions == 1
    assert adapter.issue_payloads[0] == adapter.issue_payloads[1]
    assert state["v3_pending_issue_acknowledgments"] == {}
    assert state["v3_issue_batches"]["receipt:heat-one"] == "issue_batch:recovered"


def test_ambiguous_approval_reentry_finishes_local_evidence_and_issue_once(tmp_path):
    from woodchopping.strathmark_v3_client import V3RecoveryRequired

    state, store = _v3_state(tmp_path)
    rows = _field_rows()
    state["events"].append({"handicap_results_all": rows})
    approval_row = {
        "field_id": "field:heat-one",
        "receipt_id": "receipt:heat-one",
        "receipt_content_digest": "a" * 64,
        "receipt_revision": 1,
        "upstream_field_revision": 1,
        "row_digest": "b" * 64,
        "call_order": 1,
        "decision_state": "undecided",
        "ordinary_batch_eligible": True,
        "degraded_batch_eligible": False,
        "classification": "green",
    }

    class Adapter:
        decision_calls = 0
        recoveries = 0
        acknowledgments = 0
        recovered = False

        def approval_page(self, *_args, **_kwargs):
            return {"snapshot_id": "approval_snapshot:" + "1" * 64, "rows": [approval_row]}

        def decide_approval(self, _context, payload):
            self.decision_calls += 1
            if not self.recovered:
                raise V3RecoveryRequired("approval-command:one")
            return {"action": payload["action"], "status": "accepted"}

        def retry_recovery(self, command_key, _context):
            assert command_key == "approval-command:one"
            self.recoveries += 1
            self.recovered = True
            return {"status": "recovered"}

        def acknowledge_issue(self, _context, payload):
            self.acknowledgments += 1
            return {
                "issue_batch_id": "issue_batch:recovered-approval",
                "receipt_ids": [item["receipt_id"] for item in payload["receipt_bindings"]],
            }

    adapter = Adapter()
    checkpoints = []

    first = review_v3_approval_queue(
        state,
        authority_store=store,
        v3_adapter=adapter,
        input_fn=lambda prompt: "y" if "Approve" in prompt else "c",
        checkpoint_callback=lambda root: checkpoints.append(deepcopy(root)) or True,
    )

    assert first == []
    assert "v3_pending_approval_decision" in state
    assert any("v3_pending_approval_decision" in saved for saved in checkpoints)

    second = review_v3_approval_queue(
        state,
        authority_store=store,
        v3_adapter=adapter,
        input_fn=lambda _prompt: "r",
        checkpoint_callback=lambda root: checkpoints.append(deepcopy(root)) or True,
    )

    assert second == [{"action": "ordinary_batch_accept", "status": "accepted"}]
    assert adapter.recoveries == 1
    assert adapter.acknowledgments == 1
    assert state["prediction_review_evidence"] == [
        {
            "field_id": "field:heat-one",
            "classification": "green",
            "interventions": ["ordinary_batch_accept"],
        }
    ]
    assert rows[0]["issue_batch_id"] == "issue_batch:recovered-approval"
    assert "v3_pending_approval_decision" not in state


def test_recorded_unsettled_round_retries_without_duplicate_excel_write(tmp_path):
    state, store = _v3_state(tmp_path)
    rows = _field_rows()
    round_object = {
        "round_name": "Heat 1",
        "handicap_results": rows,
        "actual_results": {"Alice": 30.125, "Bob": 32.5},
    }
    event = {"event_name": "300mm SB", "rounds": [round_object]}
    state["events"].append(event)
    state["v3_issue_batches"] = {"receipt:heat-one": "issue_batch:one"}
    writes = []

    class Adapter:
        calls = 0
        payloads = []

        def settle_result(self, _context, payload):
            self.calls += 1
            self.payloads.append(payload)
            if self.calls == 1:
                raise __import__("woodchopping.strathmark_v3_client", fromlist=["V3ClientError"]).V3ClientError(
                    "temporarily blocked"
                )
            return {
                "schema_version": "strathmark-v3-settlement-response-v1",
                "settlement_id": "settlement:one",
                "receipt_id": "receipt:heat-one",
                "status": "recorded",
            }

    adapter = Adapter()

    def write_once():
        writes.append("excel")
        return True

    assert not record_and_settle_v3_round(
        state,
        event,
        round_object,
        write_action=write_once,
        authority_store=store,
        v3_adapter=adapter,
    )
    assert round_object["canonical_results_recorded"] is True
    assert round_object["v3_settlement_status"] == "recorded_unsettled"

    assert record_and_settle_v3_round(
        state,
        event,
        round_object,
        write_action=write_once,
        authority_store=store,
        v3_adapter=adapter,
    )

    assert writes == ["excel"]
    assert round_object["v3_settlement_status"] == "settled"
    payload = adapter.payloads[-1]
    assert adapter.payloads[0] == adapter.payloads[1]
    assert payload["issue_batch_id"] == "issue_batch:one"
    assert payload["receipt_id"] == "receipt:heat-one"
    assert payload["results"] == [
        {
            "competitor_id": "competitor:alice",
            "status": "completion",
            "raw_time_ms": 30125,
            "penalty_ms": None,
            "source_revision": 1,
        },
        {
            "competitor_id": "competitor:bob",
            "status": "completion",
            "raw_time_ms": 32500,
            "penalty_ms": None,
            "source_revision": 1,
        },
    ]


def test_ambiguous_settlement_uses_exact_recovery_without_v2_or_rewrite(tmp_path):
    from woodchopping.strathmark_v3_client import V3RecoveryRequired

    state, store = _v3_state(tmp_path)
    rows = _field_rows()
    round_object = {
        "handicap_results": rows,
        "actual_results": {"Alice": 30.0, "Bob": 31.0},
    }
    state["v3_issue_batches"] = {"receipt:heat-one": "issue_batch:one"}
    writes = []

    class Adapter:
        calls = 0
        recovered = []

        def settle_result(self, _context, _payload):
            self.calls += 1
            if self.calls == 1:
                raise V3RecoveryRequired("strathex-settle-one")
            return {
                "settlement_id": "settlement:one",
                "receipt_id": "receipt:heat-one",
                "status": "recovered",
            }

        def retry_recovery(self, command_key, context):
            self.recovered.append((command_key, context.scope_id))
            return {"status": "recovered"}

    adapter = Adapter()
    assert record_and_settle_v3_round(
        state,
        {},
        round_object,
        write_action=lambda: writes.append("excel") or True,
        authority_store=store,
        v3_adapter=adapter,
        input_fn=lambda _prompt: "r",
    )
    assert writes == ["excel"]
    assert adapter.recovered == [("strathex-settle-one", "tournament:show")]


def test_v2_recording_is_unchanged_and_does_not_call_v3(tmp_path):
    store = PredictionAuthorityStore(tmp_path / "authority.db")
    created = store.create_scope(owner_kind="tournament", scope_id="tournament:v2")
    selected = store.select_engine(
        created.reference,
        engine="v2",
        actor="actor:judge-one",
        selected_at="2026-08-27T16:00:00.000Z",
        reason_code="judge_selection",
        mode="production",
        contract_identity="contract:v2",
        source_identity="source:v2",
    )
    state = {"events": []}
    attach_authority_reference(state, selected.reference)
    writes = []

    class Adapter:
        def settle_result(self, *_args, **_kwargs):
            raise AssertionError("V3 must not run for V2")

    assert record_and_settle_v3_round(
        state,
        {},
        {},
        write_action=lambda: writes.append("excel") or True,
        authority_store=store,
        v3_adapter=Adapter(),
    )
    assert writes == ["excel"]


def test_single_event_v3_settlement_uses_root_authority_and_write_once_retry(tmp_path):
    from woodchopping.strathmark_v3_client import V3ClientError

    store = PredictionAuthorityStore(tmp_path / "authority.db")
    created = store.create_scope(owner_kind="single_event", scope_id="tournament:single-show")
    selected = store.select_engine(
        created.reference,
        engine="v3",
        actor="actor:judge-one",
        selected_at="2026-08-27T16:00:00.000Z",
        reason_code="judge_selection",
        mode="rehearsal",
        contract_identity="contract:v3",
        source_identity="c" * 40,
    )
    locked = store.lock(
        selected.reference,
        boundary="first_authoritative_numeric_action",
        locked_at="2026-08-27T16:00:01.000Z",
    )
    state = {"rounds": []}
    attach_authority_reference(state, locked.reference)
    rows = _field_rows()
    round_object = {
        "round_name": "Final",
        "handicap_results": rows,
        "actual_results": {"Alice": 29.25, "Bob": 30.75},
    }
    state["rounds"].append(round_object)
    state["v3_issue_batches"] = {"receipt:heat-one": "issue_batch:single"}
    writes = []

    class Adapter:
        payloads = []

        def settle_result(self, _context, payload):
            self.payloads.append(payload)
            if len(self.payloads) == 1:
                raise V3ClientError("retry later")
            return {
                "settlement_id": "settlement:single",
                "receipt_id": "receipt:heat-one",
                "status": "recorded",
            }

    adapter = Adapter()

    def writer():
        writes.append("excel")
        return True

    assert not record_and_settle_v3_single_event(
        state,
        round_object,
        write_action=writer,
        authority_store=store,
        v3_adapter=adapter,
    )
    assert record_and_settle_v3_single_event(
        state,
        round_object,
        write_action=writer,
        authority_store=store,
        v3_adapter=adapter,
    )

    assert writes == ["excel"]
    assert adapter.payloads[0] == adapter.payloads[1]
    assert round_object["v3_settlement_status"] == "settled"


def test_single_event_v2_recording_remains_direct(tmp_path):
    store = PredictionAuthorityStore(tmp_path / "authority.db")
    created = store.create_scope(owner_kind="single_event", scope_id="tournament:single-v2")
    selected = store.select_engine(
        created.reference,
        engine="v2",
        actor="actor:judge-one",
        selected_at="2026-08-27T16:00:00.000Z",
        reason_code="judge_selection",
        mode="production",
        contract_identity="contract:v2",
        source_identity="source:v2",
    )
    state = {"rounds": []}
    attach_authority_reference(state, selected.reference)
    writes = []

    class Adapter:
        def settle_result(self, *_args, **_kwargs):
            raise AssertionError("V3 must not run for a V2 single event")

    assert record_and_settle_v3_single_event(
        state,
        {},
        write_action=lambda: writes.append("excel") or True,
        authority_store=store,
        v3_adapter=Adapter(),
    )
    assert writes == ["excel"]
