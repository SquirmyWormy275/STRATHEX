"""Tests for reproducible STRATHMARK evidence cutoffs in tournament state."""

from datetime import date, datetime, timedelta, timezone

import pytest

from woodchopping.prediction_context import ensure_competition_id, ensure_prediction_as_of
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
