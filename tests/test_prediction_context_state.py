"""Tests for reproducible STRATHMARK evidence cutoffs in tournament state."""

from datetime import date, datetime, timedelta, timezone

import pytest

import woodchopping.prediction_context as prediction_context
from woodchopping.prediction_context import ensure_competition_id, ensure_prediction_as_of
from woodchopping.ui.prediction_context import (
    AuthorityStateError,
    LegacyMigrationRequired,
    PredictionAuthorityStore,
    classify_legacy_state,
    confirm_legacy_v2,
    derive_scope_identity,
    resolve_authority_for_state,
)
from woodchopping.ui.tournament_ui import load_tournament_state, save_tournament_state


def test_multi_event_date_becomes_persisted_exclusive_cutoff():
    state = {"tournament_date": "2026-08-18"}

    cutoff = ensure_prediction_as_of(state)

    assert cutoff == date(2026, 8, 18)
    assert state["prediction_as_of"] == "2026-08-18"


def test_existing_cutoff_is_stable_when_event_date_changes():
    state = {
        "tournament_date": "2026-08-19",
        "prediction_as_of": "2026-08-18",
    }

    assert ensure_prediction_as_of(state) == date(2026, 8, 18)
    assert state["prediction_as_of"] == "2026-08-18"


def test_single_event_can_receive_an_explicit_cutoff():
    state = {}

    cutoff = ensure_prediction_as_of(state, fallback=date(2026, 8, 18))

    assert cutoff == date(2026, 8, 18)
    assert state["prediction_as_of"] == "2026-08-18"


def test_default_cutoff_uses_operator_local_date_across_utc_midnight(monkeypatch):
    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            if tz is None:
                return cls(2026, 8, 18, 18, 0, 0)
            return cls(2026, 8, 19, 1, 0, 0, tzinfo=timezone.utc).astimezone(tz)

    monkeypatch.setattr(prediction_context, "datetime", FrozenDateTime)
    state = {}

    cutoff = ensure_prediction_as_of(state)

    assert cutoff == date(2026, 8, 18)
    assert state["prediction_as_of"] == "2026-08-18"


def test_invalid_persisted_cutoff_is_rejected():
    with pytest.raises(ValueError, match="prediction_as_of"):
        ensure_prediction_as_of({"prediction_as_of": "not-a-date"})


def test_aware_datetime_cutoff_is_normalized_to_exclusive_utc_date():
    state = {
        "prediction_as_of": datetime(
            2026,
            8,
            18,
            23,
            30,
            tzinfo=timezone(timedelta(hours=-7)),
        )
    }

    assert ensure_prediction_as_of(state) == date(2026, 8, 19)
    assert state["prediction_as_of"] == "2026-08-19"


def test_aware_iso_datetime_string_is_normalized_to_exclusive_utc_date():
    state = {"prediction_as_of": "2026-08-18T23:30:00-07:00"}

    assert ensure_prediction_as_of(state) == date(2026, 8, 19)
    assert state["prediction_as_of"] == "2026-08-19"


def test_cutoff_rejects_trailing_garbage_after_date():
    with pytest.raises(ValueError, match="prediction_as_of"):
        ensure_prediction_as_of({"prediction_as_of": "2026-08-18garbage"})


def test_competition_id_is_namespaced_and_stable_in_event_state():
    state = {}

    first = ensure_competition_id(state)

    assert first.startswith("strathex:")
    assert ensure_competition_id(state) == first
    assert state["competition_id"] == first


def test_invalid_existing_competition_id_is_rejected():
    with pytest.raises(ValueError, match="competition_id"):
        ensure_competition_id({"competition_id": "not namespaced"})


def test_cutoff_identity_and_v2_metadata_survive_state_round_trip(tmp_path):
    state = {
        "event_name": "Persistence Cup",
        "format": "single_heat",
        "rounds": [],
        "prediction_as_of": "2026-08-18",
        "competition_id": "strathex:event-001",
        "handicap_results_all": [
            {
                "competitor_id": "C001",
                "name": "Alice Axe",
                "engine_version": "2.0.0",
                "optimizer": "posterior_crn_v2",
            }
        ],
    }
    path = tmp_path / "state.json"

    assert save_tournament_state(state, str(path))
    restored = load_tournament_state(str(path))

    assert restored["prediction_as_of"] == "2026-08-18"
    assert restored["competition_id"] == "strathex:event-001"
    assert restored["handicap_results_all"] == state["handicap_results_all"]


def test_selection_receipt_is_canonical_in_sqlite_and_json_contains_only_reference(tmp_path):
    store = PredictionAuthorityStore(tmp_path / "authority.db")
    receipt = store.create_scope(owner_kind="single_event", scope_id="strathex:single-001")

    selected = store.select_engine(
        receipt.reference,
        engine="v3",
        actor="judge:local",
        selected_at="2026-08-27T15:00:00Z",
        reason_code="evaluation",
        reason_note="Compare the new engine on a real field",
        mode="rehearsal",
        contract_identity="v3-consumer/1",
        source_identity="strathmark:abc123",
    )

    assert selected.engine == "v3"
    assert selected.locked is False
    assert selected.reference.scope_id == "strathex:single-001"
    assert store.resolve(selected.reference) == selected
    assert set(selected.reference.to_json()) == {"authority_store_id", "scope_id", "revision", "digest", "save_id"}
    assert "judge:local" not in str(selected.reference.to_json())
    assert "evaluation" not in str(selected.reference.to_json())


def test_engine_change_requires_reason_and_is_impossible_after_lock(tmp_path):
    store = PredictionAuthorityStore(tmp_path / "authority.db")
    created = store.create_scope(owner_kind="single_event", scope_id="strathex:single-002")
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

    with pytest.raises(AuthorityStateError, match="reason"):
        store.select_engine(
            v2.reference,
            engine="v3",
            actor="judge:local",
            selected_at="2026-08-27T15:01:00Z",
            reason_code="",
            mode="rehearsal",
            contract_identity="v3-consumer/1",
            source_identity="strathmark:abc123",
        )

    locked = store.lock(v2.reference, boundary="authoritative_calculation", locked_at="2026-08-27T15:02:00Z")
    with pytest.raises(AuthorityStateError, match="locked"):
        store.select_engine(
            locked.reference,
            engine="v3",
            actor="judge:local",
            selected_at="2026-08-27T15:03:00Z",
            reason_code="evaluation",
            mode="rehearsal",
            contract_identity="v3-consumer/1",
            source_identity="strathmark:abc123",
        )


def test_deterministic_child_identities_are_stable_and_revision_sensitive():
    first = derive_scope_identity("strathex:root-001", "round", "final", revision=1)

    assert first == derive_scope_identity("strathex:root-001", "round", "final", revision=1)
    assert first.startswith("strathex:round:")
    assert first != derive_scope_identity("strathex:root-001", "round", "final", revision=2)
    assert first != derive_scope_identity("strathex:other-root", "round", "final", revision=1)


def test_unselected_scope_and_legacy_states_block_numeric_resolution(tmp_path):
    store = PredictionAuthorityStore(tmp_path / "authority.db")
    created = store.create_scope(owner_kind="single_event", scope_id="strathex:unselected")
    state = {"prediction_authority_ref": created.reference.to_json(), "rounds": []}

    with pytest.raises(LegacyMigrationRequired, match="selection_required"):
        resolve_authority_for_state(state, store)
    assert classify_legacy_state({"rounds": []}) == "selection_required"


def test_legacy_v2_confirmation_is_explicit_and_mixed_provenance_stays_blocked(tmp_path):
    store = PredictionAuthorityStore(tmp_path / "authority.db")
    legacy_v2 = {
        "rounds": [],
        "handicap_results_all": [{"name": "Alice", "mark": 3, "engine_version": "2.0.0"}],
    }
    mixed = {
        "rounds": [],
        "handicap_results_all": [
            {"name": "Alice", "mark": 3, "engine_version": "2.0.0"},
            {"name": "Bob", "mark": 4, "engine_version": "3.0.0"},
        ],
    }

    assert classify_legacy_state(legacy_v2) == "legacy_v2_confirmation_required"
    receipt = confirm_legacy_v2(
        legacy_v2,
        store,
        actor="judge:local",
        confirmed_at="2026-08-27T15:00:00Z",
        contract_identity="v2/2.0.0",
        source_identity="strathmark:a231ad6",
    )
    assert receipt.engine == "v2"
    assert legacy_v2["prediction_authority_ref"] == receipt.reference.to_json()
    assert classify_legacy_state(mixed) == "reconciliation_required"
    with pytest.raises(LegacyMigrationRequired, match="reconciliation_required"):
        confirm_legacy_v2(
            mixed,
            store,
            actor="judge:local",
            confirmed_at="2026-08-27T15:00:00Z",
            contract_identity="v2/2.0.0",
            source_identity="strathmark:a231ad6",
        )
