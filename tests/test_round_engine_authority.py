"""Advancing rounds must remain bound to one explicit engine authority."""

from __future__ import annotations

from copy import deepcopy

import pandas as pd
import pytest

from woodchopping.engine_selection import EngineRouter
from woodchopping.ui.bracket_ui import generate_bracket_seeds
from woodchopping.ui.prediction_context import (
    PredictionAuthorityStore,
    attach_authority_reference,
    derive_scope_identity,
)
from woodchopping.ui.tournament_ui import distribute_competitors_into_heats, generate_next_round
from woodchopping.ui.v52_helpers import manage_scratches


def _selected_tournament(tmp_path, *, engine: str):
    store = PredictionAuthorityStore(tmp_path / f"{engine}-authority.db")
    created = store.create_scope(owner_kind="tournament", scope_id=f"tournament:{engine}:rounds")
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
    names = [f"Chopper {index}" for index in range(1, 7)]
    roster = pd.DataFrame(
        {
            "competitor_id": [f"C{index:03d}" for index in range(1, 7)],
            "competitor_name": names,
        }
    )
    root = {}
    attach_authority_reference(root, selected.reference)
    event = {
        "event_id": "event_7",
        "all_competitors_df": roster,
        "rounds": [{"round_type": "heat"}],
        "num_stands": 3,
        "wood_species": "S01",
        "wood_diameter": 300,
        "wood_quality": 5,
        "event_code": "SB",
        "prediction_as_of": "2026-08-26",
    }
    return root, event, store, names


def _projection(request, *, engine_version: str, include_mark: bool):
    rows = []
    for index, competitor_id in enumerate(request["ordered_competitor_ids"]):
        row = {
            "name": request["competitor_names"][competitor_id],
            "predicted_time": 20.0 + index,
            "engine_version": engine_version,
        }
        if include_mark:
            row["mark"] = 3 + index
        rows.append(row)
    return rows


def test_v3_advancing_stage_seeds_then_materializes_each_actual_heat(tmp_path, monkeypatch):
    root, event, store, names = _selected_tournament(tmp_path, engine="v3")
    monkeypatch.setattr("woodchopping.data.load_results_df", lambda: pd.DataFrame())
    forecast_calls = []
    exact_calls = []

    def forecast(*, execution_context, **request):
        forecast_calls.append(request)
        return _projection(request, engine_version="3.0.0", include_mark=False)

    def exact(*, execution_context, **request):
        exact_calls.append(request)
        return _projection(request, engine_version="3.0.0", include_mark=True)

    rounds = generate_next_round(
        event,
        names,
        "semi",
        authority_store=store,
        engine_router=EngineRouter(
            v2_adapter=lambda **request: pytest.fail(f"V2 fallback forbidden: {request}"),
            v3_adapter=exact,
        ),
        forecast_adapter=forecast,
        authority_checkpoint_callback=lambda _state: True,
        authority_child=event,
        authority_root_state=root,
    )

    assert len(forecast_calls) == 1
    assert len(exact_calls) == len(rounds) == 2
    authority = store.resolve(root["prediction_authority_ref"])
    expected_field_ids = {
        derive_scope_identity(
            authority.reference.scope_id,
            "field",
            f"event:event_7:stage:semi:generation:1:heat:{heat_index}",
        )
        for heat_index in (1, 2)
    }
    expected_round_ids = {
        derive_scope_identity(
            authority.reference.scope_id,
            "round",
            f"event:event_7:stage:semi:generation:1:heat:{heat_index}",
        )
        for heat_index in (1, 2)
    }
    assert {request["field_id"] for request in exact_calls} == expected_field_ids
    assert {request["round_id"] for request in exact_calls} == expected_round_ids
    assert {round_object["v3_round_id"] for round_object in rounds} == expected_round_ids
    assert all(all("mark" in row for row in round_object["handicap_results"]) for round_object in rounds)
    assert all(len(round_object["handicap_results"]) == len(round_object["competitors"]) for round_object in rounds)


def test_v2_advancing_stage_uses_v2_for_seeding_and_each_exact_heat(tmp_path, monkeypatch):
    root, event, store, names = _selected_tournament(tmp_path, engine="v2")
    monkeypatch.setattr("woodchopping.data.load_results_df", lambda: pd.DataFrame())
    calls = []

    def v2(**request):
        calls.append(request)
        return _projection(request, engine_version="2.0.0", include_mark=True)

    rounds = generate_next_round(
        event,
        names,
        "semi",
        authority_store=store,
        engine_router=EngineRouter(v2_adapter=v2),
        forecast_adapter=lambda **request: pytest.fail(f"V3 forecast forbidden: {request}"),
        authority_checkpoint_callback=lambda _state: True,
        authority_child=event,
        authority_root_state=root,
    )

    assert len(calls) == 3  # one advancing-field seed calculation, then one per actual heat
    assert len({request["field_id"] for request in calls[1:]}) == 2
    assert all(row["engine_version"].startswith("2.") for heat in rounds for row in heat["handicap_results"])
    assert all("v3_round_id" not in heat for heat in rounds)


def test_advancing_round_requires_authority_and_never_falls_back(tmp_path, monkeypatch):
    _, event, _, names = _selected_tournament(tmp_path, engine="v2")
    monkeypatch.setattr("woodchopping.data.load_results_df", lambda: pd.DataFrame())

    with pytest.raises(ValueError, match="prediction authority"):
        generate_next_round(event, names, "semi")


def test_v3_advancing_failure_propagates_without_v2_fallback(tmp_path, monkeypatch):
    root, event, store, names = _selected_tournament(tmp_path, engine="v3")
    monkeypatch.setattr("woodchopping.data.load_results_df", lambda: pd.DataFrame())

    def exact(*, execution_context, **request):
        raise RuntimeError("exact-field V3 unavailable")

    with pytest.raises(RuntimeError, match="exact-field V3 unavailable"):
        generate_next_round(
            event,
            names,
            "semi",
            authority_store=store,
            engine_router=EngineRouter(
                v2_adapter=lambda **request: pytest.fail(f"V2 fallback forbidden: {request}"),
                v3_adapter=exact,
            ),
            forecast_adapter=lambda execution_context, **request: _projection(
                request, engine_version="3.0.0", include_mark=False
            ),
            authority_checkpoint_callback=lambda _state: True,
            authority_child=event,
            authority_root_state=root,
        )


def test_mixed_mark_and_prefield_seed_evidence_is_rejected():
    roster = pd.DataFrame({"competitor_name": ["Marked", "Forecast"]})

    with pytest.raises(ValueError, match="mixes issued marks"):
        distribute_competitors_into_heats(
            roster,
            [
                {"name": "Marked", "predicted_time": 20.0, "mark": 3},
                {"name": "Forecast", "predicted_time": 21.0},
            ],
            2,
            1,
        )


def test_championship_advancing_round_stays_mark_three_without_engine_calls(tmp_path):
    _, event, _, names = _selected_tournament(tmp_path, engine="v3")

    rounds = generate_next_round(event, names[:3], "final", is_championship=True)

    assert len(rounds) == 1
    assert {row["mark"] for row in rounds[0]["handicap_results"]} == {3}


def test_bracket_seeding_rejects_missing_authority_context(monkeypatch):
    monkeypatch.setattr("woodchopping.data.load_results_df", lambda: pd.DataFrame())
    roster = pd.DataFrame({"competitor_name": ["Alice", "Bob"]})

    with pytest.raises(ValueError, match="prediction authority"):
        generate_bracket_seeds(roster, "S01", 300, 5, "SB")


def test_v3_bracket_seeding_uses_prefield_forecast_without_exact_or_v2(tmp_path, monkeypatch):
    root, event, store, _ = _selected_tournament(tmp_path, engine="v3")
    monkeypatch.setattr("woodchopping.data.load_results_df", lambda: pd.DataFrame())
    forecast_calls = []

    def forecast(*, execution_context, **request):
        forecast_calls.append(request)
        return _projection(request, engine_version="3.0.0", include_mark=False)

    predictions = generate_bracket_seeds(
        event["all_competitors_df"],
        "S01",
        300,
        5,
        "SB",
        root_state=root,
        authority_child=event,
        authority_store=store,
        engine_router=EngineRouter(
            v2_adapter=lambda **request: pytest.fail(f"V2 fallback forbidden: {request}"),
            v3_adapter=lambda **request: pytest.fail(f"exact-field call forbidden: {request}"),
        ),
        forecast_adapter=forecast,
        authority_checkpoint_callback=lambda _state: True,
    )

    assert len(forecast_calls) == 1
    assert set(predictions) == set(event["all_competitors_df"]["competitor_name"])
    assert all("mark" not in prediction for prediction in predictions.values())


def test_bracket_scratch_regeneration_fails_before_mutation_without_authority(monkeypatch):
    event = {
        "event_id": "event_1",
        "event_name": "Bracket",
        "event_type": "bracket",
        "all_competitors": ["Alice", "Bob"],
        "all_competitors_df": pd.DataFrame({"competitor_name": ["Alice", "Bob"]}),
        "competitor_status": {"Alice": "active", "Bob": "active"},
        "rounds": [{"matches": [{"status": "pending"}]}],
    }
    state = {
        "tournament_roster": [
            {"competitor_name": "Alice", "events_entered": ["event_1"]},
            {"competitor_name": "Bob", "events_entered": ["event_1"]},
        ],
        "events": [event],
    }
    before = deepcopy(state)
    answers = iter(["1", "y"])
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(answers))

    with pytest.raises(ValueError, match="prediction authority"):
        manage_scratches(state)

    assert state["events"][0]["competitor_status"] == before["events"][0]["competitor_status"]
    assert state["events"][0]["all_competitors"] == before["events"][0]["all_competitors"]
