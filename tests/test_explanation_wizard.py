"""Focused contract tests for the judge-facing ASCII explanation Wizard."""

from __future__ import annotations

import pytest

import explanation_system_functions as explanations


def _answers(*values: str):
    answers = iter(values)

    def answer(_prompt: str = "") -> str:
        return next(answers)

    return answer


def _recorded_answers(prompts: list[str], *values: str):
    answers = iter(values)

    def answer(prompt: str = "") -> str:
        prompts.append(prompt)
        return next(answers)

    return answer


def test_complete_ascii_wizard_tour_teaches_current_v2_v3_system(capsys):
    explanations.explanation_menu(input_fn=_answers("1", "", "", "", "", "", "0"))

    output = capsys.readouterr().out
    normalized = output.lower()

    assert "the strathex wizard" in normalized
    assert "grimoire" in normalized
    assert "larger mark starts later" in normalized
    assert "mark + raw cutting time" in normalized
    assert "common translation" in normalized
    assert "strathex manages the competition" in normalized
    assert "strathmark supplies numeric forecasts" in normalized
    assert "v2" in normalized and "deterministic production" in normalized
    assert "formula assessor" in normalized
    assert "hierarchical ml assessor" in normalized
    assert "three-member llm council" in normalized
    assert "independent forecast" in normalized
    assert "accuracy-earned" in normalized
    assert "pre-field" in normalized and "cannot contain a mark" in normalized
    assert "exact field" in normalized
    assert "rehearsal-only" in normalized
    assert "single event" in normalized
    assert "tournament root" in normalized and "inherits" in normalized
    assert "no default" in normalized and "no silent fallback" in normalized
    assert "readiness" in normalized and "locks" in normalized
    assert "recovery" in normalized and "audit" in normalized
    assert "championship" in normalized and "bracket mark 3" in normalized
    assert "judge reviews" in normalized

    # The retired winner-take-all cascade and its old concrete model are not
    # the current architecture and must not return with the character.
    assert "highest-confidence prediction wins" not in normalized
    assert "qwen2.5:7b" not in normalized


def test_wizard_h_path_keeps_concise_selector_help(capsys):
    explanations.explanation_menu(input_fn=_answers("h", "", "0"))

    output = capsys.readouterr().out.lower()
    assert "choosing strathmark v2 or v3" in output
    assert "no silent fallback" in output
    assert "rehearsal" in output
    assert "the strathex wizard" in output


@pytest.mark.parametrize(
    ("choice", "answers", "expected"),
    [
        ("2", ("2", "", "0"), "the two clocks"),
        ("3", ("3", "", "", "0"), "two grimoires, not one cascade"),
        ("4", ("4", "", "0"), "the deliberate choice"),
        ("5", ("5", "", "0"), "the judge still wears the hat"),
    ],
)
def test_numbered_scrolls_route_to_the_requested_topic(choice, answers, expected, capsys):
    explanations.explanation_menu(input_fn=_answers(*answers))

    output = capsys.readouterr().out.lower()
    assert expected in output, f"scroll {choice} did not render its topic"


def test_invalid_scroll_returns_to_the_index(capsys):
    explanations.explanation_menu(input_fn=_answers("not-a-rune", "0"))

    output = capsys.readouterr().out.lower()
    assert "that rune is not in the index" in output
    assert output.count("select a scroll:") == 0
    assert output.count("the strathex wizard") == 2


def test_ascii_wizard_banner_has_straight_70_character_borders(capsys):
    explanations._wizard_banner()

    rows = [line for line in capsys.readouterr().out.splitlines() if line]
    assert rows
    assert all(line.isascii() for line in rows)
    assert all(len(line) == 70 for line in rows)


def test_pause_labels_match_the_screen_that_receives_control(capsys):
    prompts = []
    explanations.show_prediction_engine_help(input_fn=_recorded_answers(prompts, ""))
    assert "continue" in prompts[-1].lower()
    assert "wizard" not in prompts[-1].lower()

    prompts.clear()
    explanations.explanation_menu(input_fn=_recorded_answers(prompts, "1", "", "", "", "", "", "0"))
    assert any("return to the index" in prompt.lower() for prompt in prompts)
    assert not any("close the grimoire" in prompt.lower() for prompt in prompts)
    capsys.readouterr()
