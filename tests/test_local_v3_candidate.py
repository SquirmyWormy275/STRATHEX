"""Local V3 transport invariants; actual numerics are checked by the installed smoke."""

import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

from woodchopping.engine_selection import EngineRouter, PredictionExecutionContext
from woodchopping.strathmark_v3_client import V3ClientError, V3RuntimeConfigurationError, build_v3_runtime
from woodchopping.strathmark_v3_local import LOCAL_V3_CONTRACT_DIGEST, LOCAL_V3_PROTOCOL, LocalV3Candidate
from woodchopping.ui.multi_event_ui import select_prediction_engine_for_scope
from woodchopping.ui.prediction_context import PredictionAuthorityStore, resolve_authority_for_state


def local_candidate(tmp_path, monkeypatch):
    identity = {
        "protocol": LOCAL_V3_PROTOCOL,
        "contract_digest": LOCAL_V3_CONTRACT_DIGEST,
        "purpose": "numeric_preview_only",
        "production_ready": False,
        "assessors": {"formula": "available", "ml": "available", "llm_council": "unavailable"},
        "source_digest": "a" * 64,
        "formula_digest": "b" * 64,
        "ml_bundle_digest": "c" * 64,
        "package_version": "3.0.0rc3",
    }
    monkeypatch.setattr(LocalV3Candidate, "_run", lambda self, *args: identity)
    workbook = tmp_path / "synthetic.xlsx"
    workbook.write_bytes(b"synthetic snapshot bytes; no operator data")
    candidate = LocalV3Candidate(
        python=Path(__file__), ml_bundle=tmp_path, workbook=workbook, snapshot_root=tmp_path / "snapshots"
    )
    return candidate, identity


def locked_context(tmp_path, candidate):
    store = PredictionAuthorityStore(tmp_path / "authority.db")
    state = {}
    answers = iter(["2", "numeric_rehearsal", ""])
    selected = select_prediction_engine_for_scope(
        state,
        authority_store=store,
        owner_kind="tournament",
        readiness_provider=candidate.selector_readiness,
        input_fn=lambda _: next(answers),
        selected_at="2026-10-02T00:00:00.000Z",
    )
    locked = store.lock(
        selected.reference, boundary="first_authoritative_numeric_action", locked_at="2026-10-02T00:00:00.000Z"
    )
    state["prediction_authority_ref"] = locked.reference.to_json()
    return PredictionExecutionContext.from_receipt(locked), state


def test_local_choice_persists_and_children_cannot_override(tmp_path, monkeypatch):
    candidate, _ = local_candidate(tmp_path, monkeypatch)
    context, state = locked_context(tmp_path, candidate)
    reopened = PredictionAuthorityStore(tmp_path / "authority.db")
    receipt = resolve_authority_for_state(state, reopened, child={"event_code": "UH"})
    assert receipt.engine == "v3" and receipt.locked
    assert receipt.contract_identity == LOCAL_V3_CONTRACT_DIGEST
    assert receipt.pre_field_signer_trust is None
    assert PredictionExecutionContext.from_receipt(receipt) == context
    with pytest.raises(ValueError, match="child"):
        resolve_authority_for_state(
            state, reopened, child={"prediction_authority_ref": state["prediction_authority_ref"]}
        )


def test_snapshot_is_frozen_across_live_changes_and_tamper_rejected(tmp_path, monkeypatch):
    candidate, _ = local_candidate(tmp_path, monkeypatch)
    context, _ = locked_context(tmp_path, candidate)
    snapshot = candidate._snapshot(context, "2026-10-02T00:00:00.000Z")
    expected = snapshot.read_bytes()
    candidate.workbook.write_bytes(b"later workbook contents")
    assert candidate._snapshot(context, "2026-10-02T00:00:00.000Z").read_bytes() == expected
    with pytest.raises(V3ClientError, match="cutoff"):
        candidate._snapshot(context, "2026-10-03T00:00:00.000Z")
    snapshot.chmod(0o600)
    snapshot.write_bytes(b"tampered")
    with pytest.raises(V3ClientError, match="digest"):
        candidate._snapshot(context, "2026-10-02T00:00:00.000Z")


def test_model_change_blocks_work_and_never_calls_v2(tmp_path, monkeypatch):
    candidate, identity = local_candidate(tmp_path, monkeypatch)
    context, _ = locked_context(tmp_path, candidate)
    identity["ml_bundle_digest"] = "d" * 64
    with pytest.raises(V3ClientError, match="changed"):
        EngineRouter(v2_adapter=lambda **_: pytest.fail("V2 fallback"), v3_adapter=candidate).calculate_field(
            context,
            competitors_df=None,
        )


@pytest.mark.parametrize(
    "method", ["approval_page", "decide_approval", "acknowledge_issue", "settle_result", "close_round"]
)
def test_local_candidate_cannot_issue_or_settle(tmp_path, monkeypatch, method):
    candidate, _ = local_candidate(tmp_path, monkeypatch)
    with pytest.raises(V3ClientError, match="full authenticated V7 runtime"):
        getattr(candidate, method)()


def test_wrong_authority_rejected_before_any_numeric_request(tmp_path, monkeypatch):
    candidate, _ = local_candidate(tmp_path, monkeypatch)
    context, _ = locked_context(tmp_path, candidate)
    with pytest.raises(V3ClientError, match="selected numeric preview authority"):
        candidate(execution_context=replace(context, source_identity="e" * 64))


def test_mixed_local_and_service_config_is_rejected():
    with pytest.raises(V3RuntimeConfigurationError, match="one V3 profile"):
        build_v3_runtime(
            environ={"STRATHEX_V3_LOCAL_PYTHON": "/synthetic/python", "STRATHMARK_V3_BASE_URL": "http://127.0.0.1:8787"}
        )


def test_local_profile_blocks_workbook_result_write_before_settlement(tmp_path, monkeypatch):
    from woodchopping.ui.multi_event_ui import record_and_settle_v3_single_event

    candidate, _ = local_candidate(tmp_path, monkeypatch)
    _, state = locked_context(tmp_path, candidate)
    round_object = {}
    assert not record_and_settle_v3_single_event(
        state,
        round_object,
        write_action=lambda: pytest.fail("official workbook write must not happen"),
        authority_store=PredictionAuthorityStore(tmp_path / "authority.db"),
        v3_adapter=candidate,
    )
    assert not round_object.get("canonical_results_recorded")


def test_local_preview_cannot_export_official_schedule(monkeypatch, capsys):
    from woodchopping.ui.schedule_printout import display_and_export_schedule, generate_printable_schedule

    monkeypatch.setattr("builtins.input", lambda _: pytest.fail("export prompt must not be reached"))
    display_and_export_schedule(
        {"events": [{"handicap_results": [{"mark": 3, "mark_origin": "unissued_linux_numeric_preview"}]}]}
    )
    assert "cannot be exported" in capsys.readouterr().out
    with pytest.raises(ValueError, match="cannot be exported"):
        generate_printable_schedule({"handicap_results": [{"mark_origin": "unissued_linux_numeric_preview"}]})


def test_review_menu_displays_local_previews_without_requesting_approval(tmp_path, monkeypatch, capsys):
    from woodchopping.ui.multi_event_ui import review_v3_approval_queue

    candidate, _ = local_candidate(tmp_path, monkeypatch)
    _, state = locked_context(tmp_path, candidate)
    state["handicap_results_all"] = [
        {"name": "Synthetic One", "mark_origin": "unissued_linux_numeric_preview", "predicted_time": 28.5, "mark": 8},
        {"name": "Synthetic Two", "mark_origin": "unissued_linux_numeric_preview", "predicted_time": 34.0},
    ]
    assert (
        review_v3_approval_queue(
            state,
            authority_store=PredictionAuthorityStore(tmp_path / "authority.db"),
            v3_adapter=candidate,
            checkpoint_callback=lambda _: True,
        )
        == []
    )
    output = capsys.readouterr().out
    assert "predicted 28.500s | proposed Mark 8" in output
    assert "predicted 34.000s | seeding only; no mark" in output
    assert "no approval or issue authority" in output


def test_worker_timeout_is_a_typed_failure(tmp_path, monkeypatch):
    candidate = LocalV3Candidate.__new__(LocalV3Candidate)
    candidate.python, candidate.ml_bundle = tmp_path / "synthetic-python", tmp_path

    def timeout(*_args, **_kwargs):
        raise subprocess.TimeoutExpired(["synthetic-worker"], 120)

    monkeypatch.setattr(subprocess, "run", timeout)
    with pytest.raises(V3ClientError, match="could not complete"):
        candidate._run("status")


@pytest.mark.parametrize("key,value", [("source_digest", None), ("formula_digest", "invalid"), ("package_version", "")])
def test_malformed_readiness_is_a_typed_failure(tmp_path, monkeypatch, key, value):
    _, identity = local_candidate(tmp_path, monkeypatch)
    identity[key] = value
    with pytest.raises(V3ClientError, match="source identity"):
        LocalV3Candidate(
            python=Path(__file__), ml_bundle=tmp_path, workbook=tmp_path / "synthetic.xlsx", snapshot_root=tmp_path
        )


def test_root_authority_blocks_championship_exports_and_bracket_results(tmp_path, monkeypatch):
    from woodchopping.ui import multi_event_ui
    from woodchopping.ui.bracket_ui import record_match_result, sequential_match_entry_workflow
    from woodchopping.ui.schedule_printout import generate_printable_schedule

    candidate, _ = local_candidate(tmp_path, monkeypatch)
    _, state = locked_context(tmp_path, candidate)
    store = PredictionAuthorityStore(tmp_path / "authority.db")
    monkeypatch.setattr(multi_event_ui, "_prediction_authority_store", store)
    state["events"] = [{"format": "championship", "marks": [3, 3]}]
    monkeypatch.setattr("builtins.input", lambda _: pytest.fail("result prompt must not be reached"))
    assert multi_event_ui.sequential_results_workflow(state, {}, None, authority_store=store) is state
    with pytest.raises(ValueError, match="cannot be exported"):
        generate_printable_schedule(state, authority_store=store)
    assert sequential_match_entry_workflow(state) is state
    with pytest.raises(ValueError, match="official"):
        record_match_result(state, "synthetic-match", 30, 40, 1, 2)
    assert "rounds" not in state


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), -1, 0])
def test_invalid_numeric_evidence_is_rejected_before_persistence(tmp_path, monkeypatch, bad):
    import hashlib
    import json

    import pandas as pd

    candidate, identity = local_candidate(tmp_path, monkeypatch)
    context, _ = locked_context(tmp_path, candidate)
    roster = pd.DataFrame({"competitor_id": ["SYN001"], "competitor_name": ["Synthetic"]})

    def run(_self, operation, payload=None):
        if operation == "status":
            return identity
        return {
            "protocol": LOCAL_V3_PROTOCOL,
            "purpose": "numeric_preview_only",
            "issued_mark": False,
            "readiness": identity,
            "request_digest": hashlib.sha256(
                json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
            ).hexdigest(),
            "rows": [
                {
                    "competitor_id": "SYN001",
                    "predicted_time": bad,
                    "std_dev": 1,
                    "engine_version": "3.0.0rc3",
                    "method_used": "synthetic",
                }
            ],
        }

    monkeypatch.setattr(LocalV3Candidate, "_run", run)
    with pytest.raises(V3ClientError, match="invalid numeric"):
        candidate.forecast_seeding(
            execution_context=context,
            competitors_df=roster,
            round_id="round:synthetic",
            target_context={},
            ordered_competitor_ids=["competitor:synthetic"],
        )
    assert not list(candidate.snapshot_root.rglob("previews/*.json"))
