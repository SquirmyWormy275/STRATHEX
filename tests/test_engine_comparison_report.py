from __future__ import annotations

import json
from copy import deepcopy

import pytest

from woodchopping.strathmark_v3_client import V3RecoveryRequired
from woodchopping.ui import multi_event_ui
from woodchopping.ui.engine_comparison import (
    build_engine_comparison_from_completed_state,
    build_engine_comparison_record,
)
from woodchopping.ui.prediction_context import PredictionAuthorityStore, attach_authority_reference


def _record(**changes):
    values = {
        "competition_id": "competition:show-2027",
        "requested_engine": "v3",
        "requested_mode": "rehearsal",
        "returned_engine": "v3",
        "returned_model_ids": ("model:formula-v1", "model:qwen-9b"),
        "returned_bundle_ids": ("bundle:v3-demo",),
        "returned_contract_version": "strathmark.v3-consumer-contract.v5",
        "returned_contract_digest": "a" * 64,
        "returned_source_commit": "b" * 40,
        "predictions": (
            {
                "competitor_id": "competitor:b",
                "predicted_completion_ms": 51_000,
                "predicted_mark": 8,
            },
            {
                "competitor_id": "competitor:a",
                "predicted_completion_ms": 49_000,
                "predicted_mark": 3,
            },
        ),
        "outcomes": (
            {
                "competitor_id": "competitor:a",
                "actual_completion_ms": 50_000,
                "placing": 1,
                "result_status": "completion",
            },
        ),
        "reviews": (
            {
                "field_id": "field:final",
                "classification": "amber",
                "interventions": ("judge_reviewed",),
            },
        ),
        "timing_ms": {"preparation": 1200, "review": 800, "issue": None},
        "failure_count": 1,
        "recovery_count": 1,
        "judge_feedback": "Fast to scan; one amber field needed review.",
    }
    values.update(changes)
    return build_engine_comparison_record(**values)


def test_comparison_record_is_deterministic_json_and_observational_only() -> None:
    first = _record()
    second = _record(
        predictions=(
            {
                "competitor_id": "competitor:a",
                "predicted_completion_ms": 49_000,
                "predicted_mark": 3,
            },
            {
                "competitor_id": "competitor:b",
                "predicted_completion_ms": 51_000,
                "predicted_mark": 8,
            },
        ),
    )

    assert first == second
    assert json.loads(json.dumps(first, sort_keys=True)) == first
    assert first["comparison_purpose"] == "observational_only"
    assert not ({"winner", "ranking", "recommended_engine", "best_engine"} & set(first))
    assert [row["competitor_id"] for row in first["predictions_vs_outcomes"]] == [
        "competitor:a",
        "competitor:b",
    ]
    assert first["predictions_vs_outcomes"][0]["prediction_error_ms"] == -1000
    assert first["predictions_vs_outcomes"][1]["outcome_state"] == "unknown"


def test_missing_returned_evidence_and_counts_are_named_unknown_not_invented() -> None:
    record = _record(
        returned_engine=None,
        returned_model_ids=None,
        returned_bundle_ids=None,
        returned_contract_version=None,
        returned_contract_digest=None,
        returned_source_commit=None,
        predictions=(),
        outcomes=(),
        reviews=(),
        timing_ms=None,
        failure_count=None,
        recovery_count=None,
        judge_feedback=None,
    )

    assert record["returned_authority"]["engine"] == {"state": "unknown", "value": None}
    assert record["returned_authority"]["model_ids"] == {
        "state": "unknown",
        "value": None,
    }
    assert record["operational_counts"]["failure_count"] == {
        "state": "unknown",
        "value": None,
    }
    assert record["timing_ms"] == {"state": "unknown", "value": None}
    assert record["judge_feedback"] is None


@pytest.mark.parametrize(
    ("changes", "message"),
    (
        ({"competition_id": "Alex Kaper"}, "pseudonymous"),
        ({"returned_model_ids": ("Qwen Display Name",)}, "pseudonymous"),
        (
            {"predictions": ({"competitor_id": "competitor:a", "display_name": "Alice"},)},
            "unsupported prediction field",
        ),
        (
            {
                "reviews": (
                    {
                        "field_id": "field:final",
                        "classification": "green",
                        "interventions": (),
                        "credential": "secret",
                    },
                )
            },
            "unsupported review field",
        ),
    ),
)
def test_comparison_record_rejects_identity_or_secret_leakage(changes, message) -> None:
    with pytest.raises(ValueError, match=message):
        _record(**changes)


def test_review_timing_failures_and_feedback_are_exact_and_bounded() -> None:
    record = _record()

    assert record["review_summary"] == {
        "classification_counts": {"amber": 1, "green": 0, "red": 0, "unknown": 0},
        "fields": [
            {
                "classification": "amber",
                "field_id": "field:final",
                "interventions": ["judge_reviewed"],
            }
        ],
        "intervention_counts": {"judge_reviewed": 1},
    }
    assert record["timing_ms"] == {
        "state": "partial",
        "value": {"issue": None, "preparation": 1200, "review": 800},
    }
    assert record["operational_counts"]["failure_count"]["value"] == 1
    assert record["operational_counts"]["recovery_count"]["value"] == 1
    assert record["judge_feedback"].startswith("Fast to scan")

    with pytest.raises(ValueError, match="judge feedback"):
        _record(judge_feedback="x" * 2001)


def _completed_state(tmp_path, *, engine="v3", single=False):
    store = PredictionAuthorityStore(tmp_path / f"{engine}-authority.db")
    created = store.create_scope(
        owner_kind="single_event" if single else "tournament",
        scope_id=f"tournament:{engine}-show",
    )
    selected = store.select_engine(
        created.reference,
        engine=engine,
        actor="actor:judge-one",
        selected_at="2026-08-27T16:00:00.000Z",
        reason_code="judge_selection",
        mode="rehearsal" if engine == "v3" else "production",
        contract_identity="b" * 64 if engine == "v3" else "strathmark-v2/2.0.0",
        source_identity="a" * 40 if engine == "v3" else "strathmark:" + "a" * 40,
    )
    selected = store.lock(
        selected.reference,
        boundary="first_authoritative_numeric_action",
        locked_at="2026-08-27T16:01:00.000Z",
    )
    row = {
        "name": "Display Name Must Not Leak",
        "competitor_id": "competitor:stable-one",
        "mark": 3,
        "predicted_time": 30.0,
        "engine_version": "3.0.0" if engine == "v3" else "2.0.0",
        "returned_engine": engine,
    }
    if engine == "v3":
        row.update(
            {
                "receipt_id": "receipt:final-one",
                "receipt_digest": "c" * 64,
                "issue_batch_id": "issue_batch:one",
                "bundles": ["bundle:v3-demo"],
            }
        )
    round_object = {
        "round_name": "Final",
        "round_type": "final",
        "status": "completed",
        "handicap_results": [row],
        "actual_results": {"Display Name Must Not Leak": 31.25},
        "finish_order": {"Display Name Must Not Leak": 1},
    }
    if engine == "v3":
        round_object.update(
            {
                "v3_round_id": "round:final-one",
                "v3_settlement_status": "settled",
                "v3_settlement_id": "settlement:final-one",
            }
        )
    state = {
        "prediction_review_evidence": [
            {"field_id": "field:final-one", "classification": "amber", "interventions": ["judge_reviewed"]}
        ],
        "prediction_engine_timing_ms": {"completion_workflow": 1250},
        "prediction_engine_operational_counts": {"failure_count": 0, "recovery_count": 0},
    }
    if single:
        state.update(
            {
                "tournament_mode": "single_event",
                "rounds": [round_object],
                "final_results": {
                    "first_place": "Display Name Must Not Leak",
                    "all_placements": {"Display Name Must Not Leak": 1},
                },
            }
        )
    else:
        state.update(
            {
                "tournament_mode": "multi_event",
                "events_completed": 1,
                "events": [{"status": "completed", "rounds": [round_object]}],
            }
        )
    if engine == "v3":
        state.update(
            {
                "v3_issue_status": "issued",
                "v3_issue_batches": {"receipt:final-one": "issue_batch:one"},
                "returned_contract_version": "strathmark.v3-consumer-contract.v5",
            }
        )
    attach_authority_reference(state, selected.reference)
    return state, store, selected, round_object


def test_completed_state_derives_pseudonymous_observations_without_names(tmp_path):
    state, _store, authority, _round = _completed_state(tmp_path)

    record = build_engine_comparison_from_completed_state(
        state,
        authority=authority,
        judge_feedback="Easy to scan.",
    )

    assert record["requested_authority"] == {"engine": "v3", "mode": "rehearsal"}
    assert record["returned_authority"]["engine"]["value"] == "v3"
    assert record["returned_authority"]["bundle_ids"]["value"] == ["bundle:v3-demo"]
    assert record["returned_authority"]["contract_digest"]["value"] == "b" * 64
    observation = record["predictions_vs_outcomes"][0]
    assert observation["competitor_id"].startswith("competitor:")
    assert observation["predicted_completion_ms"] == 33_000
    assert observation["actual_completion_ms"] == 34_250
    assert observation["placing"] == 1
    assert "Display Name Must Not Leak" not in json.dumps(record)
    assert not ({"winner", "ranking", "recommended_engine", "best_engine"} & set(record))


def test_review_decisions_are_retained_as_pseudonymous_comparison_evidence():
    state = {}
    selected = [{"field_id": "field:final-one", "classification": "amber", "display_name": "must be ignored"}]

    multi_event_ui._record_prediction_review_evidence(state, selected, "individual_accept")
    multi_event_ui._record_prediction_review_evidence(state, selected, "individual_accept")

    assert state["prediction_review_evidence"] == [
        {
            "field_id": "field:final-one",
            "classification": "amber",
            "interventions": ["individual_accept"],
        }
    ]
    assert "display_name" not in json.dumps(state)


def test_single_event_root_builds_comparison_without_events_wrapper(tmp_path):
    state, _store, authority, _round = _completed_state(tmp_path, engine="v2", single=True)

    record = build_engine_comparison_from_completed_state(state, authority=authority)

    assert "events" not in state
    assert len(record["predictions_vs_outcomes"]) == 1
    assert record["predictions_vs_outcomes"][0]["predicted_completion_ms"] == 33_000
    assert record["predictions_vs_outcomes"][0]["actual_completion_ms"] == 34_250
    assert "Display Name Must Not Leak" not in json.dumps(record)


def test_single_event_v2_finalize_is_local_and_idempotent(tmp_path):
    state, store, authority, _round = _completed_state(tmp_path, engine="v2", single=True)
    assert authority.owner_kind == "single_event"

    first = multi_event_ui.finalize_completed_competition(
        state,
        authority_store=store,
        prompt_for_feedback=False,
    )
    second = multi_event_ui.finalize_completed_competition(
        state,
        authority_store=store,
        prompt_for_feedback=False,
    )

    assert first == second
    assert len(state["engine_comparison_records"]) == 1
    assert state["prediction_engine_closure"] == {"status": "local_comparison_complete", "engine": "v2"}


def test_single_event_v3_closes_root_round_then_scope(tmp_path):
    state, store, authority, round_object = _completed_state(tmp_path, engine="v3", single=True)
    assert authority.owner_kind == "single_event"

    class Adapter:
        calls = []

        def close_round(self, _context, payload):
            self.calls.append(("round", dict(payload)))
            return {
                "round_id": payload["round_id"],
                "closure_id": "round_closure:single-final",
                "status": "closed",
            }

        def close_scope(self, _context, payload):
            self.calls.append(("scope", dict(payload)))
            return {"scope_id": payload["scope_id"], "authority_sequence": 4, "status": "closed"}

    adapter = Adapter()
    multi_event_ui.finalize_completed_competition(
        state,
        authority_store=store,
        v3_adapter=adapter,
        prompt_for_feedback=False,
        closed_at_utc="2026-08-27T17:00:00.000Z",
    )

    assert "events" not in state
    assert [call[0] for call in adapter.calls] == ["round", "scope"]
    assert round_object["v3_round_close_receipt"]["closure_id"] == "round_closure:single-final"
    assert state["prediction_engine_closure"]["status"] == "closed"


def test_v2_finalize_appends_once_and_never_calls_v3(tmp_path):
    state, store, _authority, _round = _completed_state(tmp_path, engine="v2")

    class Adapter:
        def __getattr__(self, name):
            raise AssertionError(f"V3 must not be called for V2: {name}")

    first = multi_event_ui.finalize_completed_competition(
        state,
        authority_store=store,
        v3_adapter=Adapter(),
        prompt_for_feedback=False,
    )
    second = multi_event_ui.finalize_completed_competition(
        state,
        authority_store=store,
        v3_adapter=Adapter(),
        prompt_for_feedback=False,
    )

    assert first == second
    assert len(state["engine_comparison_records"]) == 1
    assert state["prediction_engine_closure"] == {"status": "local_comparison_complete", "engine": "v2"}


def test_v3_finalize_fails_closed_until_every_issued_receipt_is_settled(tmp_path):
    state, store, _authority, round_object = _completed_state(tmp_path)
    round_object["v3_settlement_status"] = "recorded_unsettled"

    class Adapter:
        calls = []

        def close_round(self, *_args):
            self.calls.append("round")

        def close_scope(self, *_args):
            self.calls.append("scope")

    adapter = Adapter()
    record = multi_event_ui.finalize_completed_competition(
        state,
        authority_store=store,
        v3_adapter=adapter,
        prompt_for_feedback=False,
    )

    assert record == state["engine_comparison_records"][0]
    assert adapter.calls == []
    assert state["prediction_engine_closure"]["status"] == "blocked_unsettled_receipts"
    assert state["prediction_engine_closure"]["receipt_ids"] == ["receipt:final-one"]


def test_v3_finalize_closes_exact_round_then_scope_and_is_idempotent(tmp_path):
    state, store, _authority, round_object = _completed_state(tmp_path)
    second_field = deepcopy(round_object)
    second_field["round_name"] = "Final Heat 2"
    second_field["handicap_results"][0]["competitor_id"] = "competitor:stable-two"
    second_field["handicap_results"][0]["receipt_id"] = "receipt:final-two"
    second_field["handicap_results"][0]["issue_batch_id"] = "issue_batch:two"
    second_field["v3_settlement_id"] = "settlement:final-two"
    state["events"][0]["rounds"].append(second_field)
    state["v3_issue_batches"]["receipt:final-two"] = "issue_batch:two"

    class Adapter:
        calls = []

        def close_round(self, _context, payload):
            self.calls.append(("round", dict(payload)))
            return {
                "round_id": payload["round_id"],
                "closure_id": "round_closure:final-one",
                "status": "closed",
            }

        def close_scope(self, _context, payload):
            self.calls.append(("scope", dict(payload)))
            return {"scope_id": payload["scope_id"], "authority_sequence": 9, "status": "closed"}

    adapter = Adapter()
    answers = iter(["Clear and quick."])
    first = multi_event_ui.finalize_completed_competition(
        state,
        authority_store=store,
        v3_adapter=adapter,
        input_fn=lambda _prompt: next(answers),
        closed_at_utc="2026-08-27T17:00:00.000Z",
    )
    second = multi_event_ui.finalize_completed_competition(
        state,
        authority_store=store,
        v3_adapter=adapter,
        prompt_for_feedback=False,
        closed_at_utc="2026-08-27T17:01:00.000Z",
    )

    assert first == second
    assert [item[0] for item in adapter.calls] == ["round", "scope"]
    assert adapter.calls[0][1]["round_id"] == "round:final-one"
    assert adapter.calls[1][1]["scope_id"] == "tournament:v3-show"
    assert round_object["v3_round_close_receipt"]["closure_id"] == "round_closure:final-one"
    assert state["v3_scope_close_receipt"]["authority_sequence"] == 9
    assert state["prediction_engine_closure"]["status"] == "closed"
    assert state["engine_comparison_records"][0]["judge_feedback"] == "Clear and quick."


def test_v3_close_ambiguity_uses_exact_recovery_without_fallback(tmp_path):
    state, store, _authority, _round = _completed_state(tmp_path)

    class Adapter:
        round_attempts = 0
        recovered = []

        def close_round(self, _context, payload):
            self.round_attempts += 1
            if self.round_attempts == 1:
                raise V3RecoveryRequired("strathex-close-round-one")
            return {"round_id": payload["round_id"], "closure_id": "round_closure:one", "status": "closed"}

        def retry_recovery(self, command_key, context):
            self.recovered.append((command_key, context.scope_id))
            return {"status": "recovered"}

        def close_scope(self, _context, payload):
            return {"scope_id": payload["scope_id"], "authority_sequence": 2, "status": "closed"}

    adapter = Adapter()
    multi_event_ui.finalize_completed_competition(
        state,
        authority_store=store,
        v3_adapter=adapter,
        input_fn=lambda _prompt: "r",
        prompt_for_feedback=False,
        closed_at_utc="2026-08-27T17:00:00.000Z",
    )

    assert adapter.recovered == [("strathex-close-round-one", "tournament:v3-show")]
    assert state["prediction_engine_closure"]["status"] == "closed"


def test_terminal_multi_event_path_calls_finalize_helper(monkeypatch, tmp_path):
    state, store, _authority, _round = _completed_state(tmp_path, engine="v2")
    finalized = []
    monkeypatch.setattr(
        multi_event_ui,
        "finalize_completed_competition",
        lambda root, **kwargs: finalized.append((root, kwargs)),
    )
    saved = []
    monkeypatch.setattr(
        multi_event_ui,
        "auto_save_multi_event",
        lambda root, **kwargs: saved.append((root, kwargs)),
    )
    monkeypatch.setattr("builtins.input", lambda _prompt="": "")

    returned = multi_event_ui.sequential_results_workflow(
        state,
        {},
        __import__("pandas").DataFrame(),
        authority_store=store,
        engine_router=object(),
    )

    assert returned is state
    assert len(finalized) == 1
    assert finalized[0][0] is state
    assert finalized[0][1]["authority_store"] is store
    assert saved == [(state, {"authority_store": store})]
