"""Competition authority must govern every STRATHEX numeric call site."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

from woodchopping.engine_selection import EngineRouter
from woodchopping.ui.handicap_ui import (
    build_engine_router,
    build_prediction_execution_context,
    calculate_authoritative_field,
    calculate_authoritative_seeding,
    normalize_actor_identifier,
)
from woodchopping.ui.prediction_context import (
    PredictionAuthorityStore,
    attach_authority_reference,
)


def _selected_state(tmp_path, *, engine="v2", owner_kind="single_event"):
    store = PredictionAuthorityStore(tmp_path / "authority.db")
    created = store.create_scope(owner_kind=owner_kind, scope_id=f"strathex:{owner_kind}:one")
    selected = store.select_engine(
        created.reference,
        engine=engine,
        actor="actor:judge-one",
        selected_at="2026-08-27T16:00:00.000Z",
        reason_code="judge_selection",
        mode="production" if engine == "v2" else "rehearsal",
        contract_identity=f"contract-{engine}",
        source_identity=f"source-{engine}",
    )
    state = {"events": []} if owner_kind == "tournament" else {}
    attach_authority_reference(state, selected.reference)
    return state, store


def test_actor_identifier_is_normalized_for_strathmark():
    assert normalize_actor_identifier(" Judge One ") == "actor:judge-one"
    assert normalize_actor_identifier("actor:judge-one") == "actor:judge-one"


def test_single_event_result_entry_settles_and_finalizes_selected_engine() -> None:
    source = (Path(__file__).resolve().parents[1] / "MainProgramV5_2.py").read_text(encoding="utf-8")

    assert "record_and_settle_v3_single_event(" in source
    assert "finalize_completed_competition(" in source
    assert 'derive_scope_identity(authority.scope_id, "round", "single-event")' in source


def test_first_numeric_boundary_locks_and_reconstructs_canonical_context(tmp_path):
    state, store = _selected_state(tmp_path)
    now = datetime(2026, 8, 27, 16, 1, tzinfo=timezone.utc)

    context = build_prediction_execution_context(state, store, now=now)

    canonical = store.resolve(state["prediction_authority_ref"])
    assert canonical.locked is True
    assert canonical.lock_boundary == "first_authoritative_numeric_action"
    assert context.authority_digest == canonical.reference.digest
    assert context.locked_at == "2026-08-27T16:01:00.000Z"


def test_tournament_child_inherits_root_and_child_override_is_rejected(tmp_path):
    state, store = _selected_state(tmp_path, owner_kind="tournament")
    child = {"event_name": "Underhand"}

    context = build_prediction_execution_context(state, store, child=child)
    assert context.scope_id == "strathex:tournament:one"

    child["prediction_authority_ref"] = dict(state["prediction_authority_ref"])
    with pytest.raises(ValueError, match="cannot override"):
        build_prediction_execution_context(state, store, child=child)


def test_authoritative_field_routes_v3_without_v2_fallback(tmp_path):
    state, store = _selected_state(tmp_path, engine="v3")
    competitors = pd.DataFrame({"competitor_name": ["Alice", "Bob"]})
    calls = []

    def v2(**request):
        pytest.fail(f"V2 fallback forbidden: {request}")

    def v3(*, execution_context, **request):
        calls.append((execution_context, request))
        return [
            {"name": "Alice", "mark": 3, "predicted_time": 30.0, "engine_version": "3.0.0"},
            {"name": "Bob", "mark": 8, "predicted_time": 35.0, "engine_version": "3.0.0"},
        ]

    result = calculate_authoritative_field(
        root_state=state,
        authority_store=store,
        engine_router=EngineRouter(v2_adapter=v2, v3_adapter=v3),
        field_local_id="single-event-initial",
        competitors_df=competitors,
        wood_species="S01",
        wood_diameter=300,
        wood_quality=5,
        event_code="SB",
        results_df=pd.DataFrame(),
    )

    assert [row["mark"] for row in result] == [3, 8]
    assert len(calls) == 1
    context, request = calls[0]
    assert context.selected_engine == "v3"
    assert request["field_id"].startswith("field:")
    assert len(request["ordered_competitor_ids"]) == 2
    assert set(request["competitor_names"].values()) == {"Alice", "Bob"}


def test_authoritative_field_rejects_scope_identity_overrides(tmp_path):
    state, store = _selected_state(tmp_path, engine="v3")

    with pytest.raises(ValueError, match="authority-bound numeric fields"):
        calculate_authoritative_field(
            root_state=state,
            authority_store=store,
            engine_router=EngineRouter(v2_adapter=lambda **_request: [], v3_adapter=lambda **_request: []),
            field_local_id="heat-one",
            competitors_df=pd.DataFrame({"competitor_name": ["Alice"]}),
            wood_species="S01",
            wood_diameter=300,
            wood_quality=5,
            event_code="UH",
            results_df=pd.DataFrame(),
            field_id="field:attacker-controlled",
        )


def test_unprepared_selected_v3_surfaces_lifecycle_failure_without_v2(tmp_path):
    state, store = _selected_state(tmp_path, engine="v3")
    competitors = pd.DataFrame({"competitor_name": ["Alice", "Bob"]})
    calls = []

    def v2(**request):
        calls.append("v2")
        return [{"engine_version": "2.0.0"}]

    def unprepared_v3(*, execution_context, **request):
        calls.append("v3")
        raise RuntimeError("V3 lifecycle scope is not prepared")

    with pytest.raises(RuntimeError, match="lifecycle scope is not prepared"):
        calculate_authoritative_field(
            root_state=state,
            authority_store=store,
            engine_router=EngineRouter(v2_adapter=v2, v3_adapter=unprepared_v3),
            field_local_id="heat-one",
            competitors_df=competitors,
            wood_species="S01",
            wood_diameter=300,
            wood_quality=5,
            event_code="SB",
            results_df=pd.DataFrame(),
        )

    assert calls == ["v3"]


def test_v2_adapter_receives_legacy_numeric_arguments_unchanged(tmp_path):
    state, store = _selected_state(tmp_path, engine="v2")
    competitors = pd.DataFrame({"competitor_name": ["Alice"]})
    sentinel = [{"name": "Alice", "mark": 3, "predicted_time": 30.0, "engine_version": "2.0.0"}]
    captured = []

    def v2(**request):
        captured.append(request)
        return sentinel

    result = calculate_authoritative_field(
        root_state=state,
        authority_store=store,
        engine_router=EngineRouter(v2_adapter=v2),
        field_local_id="heat-one",
        competitors_df=competitors,
        wood_species="S01",
        wood_diameter=300,
        wood_quality=5,
        event_code="UH",
        results_df=pd.DataFrame({"x": [1]}),
        prediction_as_of="2026-08-27",
    )

    assert result is sentinel
    assert captured[0]["competitors_df"] is competitors
    assert captured[0]["wood_species"] == "S01"
    assert captured[0]["event_code"] == "UH"
    assert "field_id" in captured[0]


def test_runtime_v2_adapter_filters_authority_metadata_from_legacy_calculator(tmp_path, monkeypatch):
    import woodchopping.ui.handicap_ui as handicap_ui

    state, store = _selected_state(tmp_path, engine="v2")
    competitors = pd.DataFrame({"competitor_name": ["Alice"]})
    captured = []
    sentinel = [{"name": "Alice", "mark": 3, "predicted_time": 30.0, "engine_version": "2.0.0"}]

    def legacy(*args, **kwargs):
        captured.append((args, kwargs))
        return sentinel

    monkeypatch.setattr(handicap_ui, "calculate_ai_enhanced_handicaps", legacy)
    result = calculate_authoritative_field(
        root_state=state,
        authority_store=store,
        engine_router=build_engine_router(),
        field_local_id="heat-one",
        competitors_df=competitors,
        wood_species="S01",
        wood_diameter=300,
        wood_quality=5,
        event_code="SB",
        results_df=pd.DataFrame(),
        prediction_as_of="2026-08-27",
    )

    assert result is sentinel
    assert captured[0][0][0] is competitors
    assert captured[0][0][1:5] == ("S01", 300, 5, "SB")
    assert captured[0][1] == {"prediction_as_of": "2026-08-27"}


def test_v3_seeding_requires_forecast_capability_and_never_calls_field_router(tmp_path):
    state, store = _selected_state(tmp_path, engine="v3")
    competitors = pd.DataFrame({"competitor_name": ["Alice"]})
    router = EngineRouter(
        v2_adapter=lambda **request: pytest.fail(f"V2 fallback forbidden: {request}"),
        v3_adapter=lambda **request: pytest.fail(f"field assembly is not a pre-field forecast: {request}"),
    )
    request = dict(
        root_state=state,
        authority_store=store,
        engine_router=router,
        field_local_id="bracket:seeding",
        competitors_df=competitors,
        wood_species="S01",
        wood_diameter=300,
        wood_quality=5,
        event_code="SB",
        results_df=pd.DataFrame(),
    )

    with pytest.raises(RuntimeError, match="no pre-field forecast capability"):
        calculate_authoritative_seeding(**request)

    calls = []

    def forecast(*, execution_context, **payload):
        calls.append((execution_context, payload))
        return [{"name": "Alice", "predicted_time": 30.0, "engine_version": "3.0.0"}]

    result = calculate_authoritative_seeding(**request, forecast_adapter=forecast)
    assert result[0]["name"] == "Alice"
    assert calls[0][1]["ordered_competitor_ids"]
    assert calls[0][1]["round_id"].startswith("round:")
    assert "field_id" not in calls[0][1]


def test_pre_field_forecasts_seed_heats_without_masquerading_as_marks():
    from woodchopping.ui.tournament_ui import distribute_competitors_into_heats

    roster = pd.DataFrame({"competitor_name": ["Fast", "Middle", "Slow"]})
    forecasts = [
        {"name": "Fast", "predicted_time": 20.0},
        {"name": "Middle", "predicted_time": 30.0},
        {"name": "Slow", "predicted_time": 40.0},
    ]

    heats = distribute_competitors_into_heats(roster, forecasts, 2, 2)

    assert heats[0]["competitors"][0] == "Slow"
    assert all("mark" not in row for heat in heats for row in heat["handicap_results"])


def test_championship_predictions_keep_fixed_mark_distinct_from_engine_output(tmp_path):
    from woodchopping.ui.championship_simulator import _generate_championship_predictions

    state, store = _selected_state(tmp_path, engine="v2")
    competitors = pd.DataFrame({"competitor_name": ["Alice", "Bob"]})

    def v2(**request):
        return [
            {"name": name, "mark": 99, "predicted_time": 30.0 + index, "engine_version": "2.0.0"}
            for index, name in enumerate(request["competitors_df"]["competitor_name"])
        ]

    wood = {"species": "S01", "size_mm": 300, "quality": 5, "event": "SB"}
    result = _generate_championship_predictions(
        competitors,
        wood,
        {"Alice": wood, "Bob": wood},
        results_df=pd.DataFrame(),
        root_state=state,
        authority_store=store,
        engine_router=EngineRouter(v2_adapter=v2),
    )

    assert [row["mark"] for row in result] == [3, 3]
    assert {row["mark_origin"] for row in result} == {"championship_fixed_rule"}
