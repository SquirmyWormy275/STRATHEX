"""Selection-bound routing tests for STRATHEX numeric work."""

from __future__ import annotations

import json
from dataclasses import FrozenInstanceError

import pytest

from woodchopping.engine_selection import (
    EngineAdapterUnavailableError,
    EngineResultMismatchError,
    EngineRouter,
    ExecutionContextError,
    PredictionExecutionContext,
)
from woodchopping.ui.prediction_context import PredictionAuthorityStore


def _context(tmp_path, *, engine: str, mode: str = "production") -> PredictionExecutionContext:
    store = PredictionAuthorityStore(tmp_path / "authority.db")
    created = store.create_scope(owner_kind="single_event", scope_id=f"strathex:{engine}-field")
    selected = store.select_engine(
        created.reference,
        engine=engine,
        actor="judge-1",
        selected_at="2026-08-27T16:00:00Z",
        reason_code="judge_selection",
        mode=mode,
        contract_identity=f"strathmark-{engine}-contract",
        source_identity=f"strathmark-{engine}-source",
    )
    locked = store.lock(
        selected.reference,
        boundary="first_authoritative_numeric_action",
        locked_at="2026-08-27T16:01:00Z",
    )
    return PredictionExecutionContext.from_receipt(locked)


def test_execution_context_is_an_immutable_snapshot_of_locked_authority(tmp_path):
    context = _context(tmp_path, engine="v2")

    assert context.selected_engine == "v2"
    assert context.mode == "production"
    assert context.locked is True
    assert context.authority_store_id.startswith("strathex-authority:")

    with pytest.raises(FrozenInstanceError):
        context.selected_engine = "v3"


def test_execution_context_rejects_unlocked_or_unselected_authority(tmp_path):
    store = PredictionAuthorityStore(tmp_path / "authority.db")
    created = store.create_scope(owner_kind="single_event")

    with pytest.raises(ExecutionContextError, match="selected engine"):
        PredictionExecutionContext.from_receipt(created)

    selected = store.select_engine(
        created.reference,
        engine="v2",
        actor="judge-1",
        selected_at="2026-08-27T16:00:00Z",
        reason_code="judge_selection",
        mode="production",
        contract_identity="strathmark-v2-contract",
        source_identity="strathmark-v2-source",
    )
    with pytest.raises(ExecutionContextError, match="locked"):
        PredictionExecutionContext.from_receipt(selected)


def test_v2_selection_calls_only_v2_and_returns_projection_unchanged(tmp_path):
    context = _context(tmp_path, engine="v2")
    projection = [{"name": "Alice Axe", "mark": 3, "engine_version": "2.0.0"}]
    calls = []

    def v2_adapter(**request):
        calls.append(("v2", request))
        return projection

    def v3_adapter(**request):
        pytest.fail(f"V3 must not run for a V2-selected scope: {request}")

    result = EngineRouter(v2_adapter=v2_adapter, v3_adapter=v3_adapter).calculate_field(
        context,
        competitors=["Alice Axe"],
        event_code="SB",
    )

    assert result is projection
    assert calls == [("v2", {"competitors": ["Alice Axe"], "event_code": "SB"})]


def test_v3_selection_without_wired_adapter_fails_typed_and_never_calls_v2(tmp_path):
    context = _context(tmp_path, engine="v3", mode="rehearsal")

    def v2_adapter(**request):
        pytest.fail(f"V2 fallback is forbidden: {request}")

    with pytest.raises(EngineAdapterUnavailableError, match="V3 adapter is not wired"):
        EngineRouter(v2_adapter=v2_adapter).calculate_field(context, event_code="SB")


def test_v3_selection_calls_only_v3_with_the_exact_execution_context(tmp_path):
    context = _context(tmp_path, engine="v3", mode="rehearsal")
    projection = [{"name": "Alice Axe", "mark": 3, "engine_version": "3.0.0"}]
    calls = []

    def v2_adapter(**request):
        pytest.fail(f"V2 fallback is forbidden: {request}")

    def v3_adapter(*, execution_context, **request):
        calls.append((execution_context, request))
        return projection

    result = EngineRouter(v2_adapter=v2_adapter, v3_adapter=v3_adapter).calculate_field(
        context,
        event_code="SB",
    )

    assert result is projection
    assert calls == [(context, {"event_code": "SB"})]


def test_adapter_failure_never_invokes_the_unselected_engine(tmp_path):
    context = _context(tmp_path, engine="v3", mode="rehearsal")
    calls = []

    def v2_adapter(**request):
        calls.append("v2")
        return [{"engine_version": "2.0.0"}]

    def v3_adapter(*, execution_context, **request):
        calls.append("v3")
        raise TimeoutError("service unavailable")

    with pytest.raises(TimeoutError, match="service unavailable"):
        EngineRouter(v2_adapter=v2_adapter, v3_adapter=v3_adapter).calculate_field(context)

    assert calls == ["v3"]


def test_v2_adapter_failure_never_invokes_v3(tmp_path):
    context = _context(tmp_path, engine="v2")
    calls = []

    def v2_adapter(**request):
        calls.append("v2")
        raise RuntimeError("calculation rejected")

    def v3_adapter(**request):
        calls.append("v3")
        return [{"engine_version": "3.0.0"}]

    with pytest.raises(RuntimeError, match="calculation rejected"):
        EngineRouter(v2_adapter=v2_adapter, v3_adapter=v3_adapter).calculate_field(context)

    assert calls == ["v2"]


@pytest.mark.parametrize(
    ("selected_engine", "mode", "returned_version"),
    [("v2", "production", "3.0.0"), ("v3", "rehearsal", "2.0.0")],
)
def test_returned_engine_mismatch_aborts_the_field(
    tmp_path,
    selected_engine,
    mode,
    returned_version,
):
    context = _context(tmp_path, engine=selected_engine, mode=mode)

    def adapter(**request):
        return [{"name": "Alice Axe", "mark": 3, "engine_version": returned_version}]

    router = (
        EngineRouter(v2_adapter=adapter)
        if selected_engine == "v2"
        else EngineRouter(v2_adapter=lambda **request: pytest.fail("no fallback"), v3_adapter=adapter)
    )

    with pytest.raises(EngineResultMismatchError, match="selected engine"):
        router.calculate_field(context)


def test_real_v3_client_is_a_router_adapter_without_v2_fallback(tmp_path, monkeypatch):
    from dataclasses import replace

    from woodchopping.strathmark_v3_client import (
        FROZEN_V3_CONTRACT_DIGEST,
        FROZEN_V3_SOURCE_COMMIT,
        V3HttpClient,
    )
    from woodchopping.v3_authority_store import V3CommandStore

    context = replace(
        _context(tmp_path, engine="v3", mode="rehearsal"),
        contract_identity=FROZEN_V3_CONTRACT_DIGEST,
        source_identity=FROZEN_V3_SOURCE_COMMIT,
    )
    client = V3HttpClient(
        base_url="http://127.0.0.1:8787",
        credential_provider=lambda: "credential",
        command_store=V3CommandStore(tmp_path / "commands.db"),
    )
    monkeypatch.setattr(
        client,
        "assemble_field",
        lambda _context, _payload: {
            "receipt_id": "receipt:one",
            "receipt_digest": "c" * 64,
            "canonical_receipt_json": json.dumps(
                {
                    "receipt_id": "receipt:one",
                    "ordered_competitor_ids": ["competitor:a", "competitor:b"],
                    "engine_authority": {
                        "scope_id": context.scope_id,
                        "engine": "v3",
                        "mode": context.mode,
                        "selection_digest": "d" * 64,
                        "consumer_contract_digest": context.contract_identity,
                        "source_commit": context.source_identity,
                    },
                    "marks": [
                        {"competitor_id": "competitor:a", "mark": 3},
                        {"competitor_id": "competitor:b", "mark": 8},
                    ],
                    "sections": [
                        {
                            "kind": "optimizer_frontier",
                            "payload_type": "inline",
                            "payload": {
                                "canonical_json": '{"expected_times_ms":[["competitor:a",30000],["competitor:b",35000]]}'
                            },
                        }
                    ],
                }
            ),
        },
    )

    result = EngineRouter(
        v2_adapter=lambda **_request: pytest.fail("V2 fallback is forbidden"),
        v3_adapter=client,
    ).calculate_field(
        context,
        field_id="field:one",
        upstream_field_revision=1,
        ordered_competitor_ids=["competitor:a", "competitor:b"],
    )

    assert [row["engine_version"] for row in result] == ["3.0.0", "3.0.0"]
