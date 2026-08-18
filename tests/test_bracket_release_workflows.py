"""Release regressions for bracket topology and interactive persistence."""

from __future__ import annotations

from copy import deepcopy

import pytest

from woodchopping.ui.bracket_ui import (
    generate_bracket_with_byes,
    generate_double_elimination_bracket,
    initialize_bracket_tournament,
    sequential_match_entry_workflow,
)


def _predictions(field_size: int) -> dict[str, dict[str, int]]:
    return {f"Seed {seed}": {"seed": seed} for seed in range(1, field_size + 1)}


def _source_match_for_seed(rounds: list[dict], seed: int) -> dict:
    return next(match for match in rounds[0]["matches"] if seed in (match["seed1"], match["seed2"]))


def _pre_final_branch_for_seed(rounds: list[dict], seed: int) -> str:
    """Trace a seed's first-round source to its semifinal match."""
    matches_by_id = {match["match_id"]: match for round_object in rounds for match in round_object["matches"]}
    final_id = rounds[-1]["matches"][0]["match_id"]
    match = _source_match_for_seed(rounds, seed)

    while match["advances_to"] != final_id:
        match = matches_by_id[match["advances_to"]]

    return match["match_id"]


@pytest.mark.parametrize("field_size", [5, 6, 8, 10, 13, 17])
def test_top_two_seeds_feed_opposite_pre_final_branches(field_size):
    rounds = generate_bracket_with_byes(_predictions(field_size))
    bracket_size = 2 ** (field_size - 1).bit_length()

    assert len(rounds[0]["matches"]) == bracket_size // 2
    assert _pre_final_branch_for_seed(rounds, 1) != _pre_final_branch_for_seed(rounds, 2)
    assert {
        _pre_final_branch_for_seed(rounds, 1),
        _pre_final_branch_for_seed(rounds, 2),
    } == {match["match_id"] for match in rounds[-2]["matches"]}

    bye_seeds = sorted(match["seed1"] for match in rounds[0]["matches"] if match["status"] == "bye")
    assert bye_seeds == list(range(1, bracket_size - field_size + 1))


def test_double_elimination_reuses_canonical_winners_bracket():
    bracket = generate_double_elimination_bracket(_predictions(6))
    winners_rounds = bracket["winners_rounds"]

    assert _pre_final_branch_for_seed(winners_rounds, 1) != _pre_final_branch_for_seed(winners_rounds, 2)


def _four_seed_state() -> dict:
    predictions = _predictions(4)
    state = initialize_bracket_tournament(num_stands=2, tentative_competitors=4)
    state["predictions"] = predictions
    state["rounds"] = generate_bracket_with_byes(predictions)
    state["total_rounds"] = len(state["rounds"])
    state["total_matches"] = sum(len(item["matches"]) for item in state["rounds"])
    return state


def _script_input(monkeypatch, answers: list[str]) -> None:
    scripted = iter(answers)
    monkeypatch.setattr("builtins.input", lambda _prompt="": next(scripted))


def test_sequential_workflow_saves_each_confirmed_match(monkeypatch, capsys):
    state = _four_seed_state()
    saved_states = []
    _script_input(monkeypatch, ["30", "31", "1", "y", "3"])

    def save_state(changed_state):
        saved_states.append(deepcopy(changed_state))
        return True

    result = sequential_match_entry_workflow(state, save_callback=save_state)

    assert result["completed_matches"] == 1
    assert len(saved_states) == 1
    assert saved_states[0]["completed_matches"] == 1
    assert saved_states[0]["rounds"][0]["matches"][0]["status"] == "completed"
    assert "Progress saved." in capsys.readouterr().out


def test_sequential_workflow_reports_failed_save(monkeypatch, capsys):
    state = _four_seed_state()
    _script_input(monkeypatch, ["30", "31", "1", "y", "3"])

    sequential_match_entry_workflow(state, save_callback=lambda _state: False)

    output = capsys.readouterr().out
    assert "Progress saved." not in output
    assert "could not be saved" in output


def test_sequential_workflow_without_callback_directs_user_to_menu(monkeypatch, capsys):
    state = _four_seed_state()
    _script_input(monkeypatch, ["30", "31", "1", "y", "3"])

    sequential_match_entry_workflow(state)

    output = capsys.readouterr().out
    assert "Progress saved." not in output
    assert "save from the tournament menu" in output.lower()
