from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_current_docs_name_both_repository_responsibilities() -> None:
    decision = _read("docs/solutions/architecture-decisions/competition-scoped-prediction-engine.md")

    assert "STRATHEX owns the deliberate human choice" in decision
    assert "STRATHMARK owns engine eligibility" in decision


def test_judge_docs_explain_selection_inheritance_and_no_fallback() -> None:
    guide = _read("wiki/Choosing-the-Prediction-Engine.md")

    assert "Single event: choose once during event setup" in guide
    assert "Multi-event tournament: choose once at tournament creation" in guide
    assert "never show their own selector" in guide
    assert "There is no fallback between engines" in guide


def test_v3_pre_field_forecast_is_never_documented_as_a_mark() -> None:
    required_wording = {
        "README.md": "forbidden from carrying a mark",
        "docs/CURRENT_RUNTIME_CONTRACT.md": "issued_mark=false",
        "wiki/Choosing-the-Prediction-Engine.md": "contains no mark",
    }
    for relative_path, expected_phrase in required_wording.items():
        text = _read(relative_path)
        assert "pre-field" in text
        assert expected_phrase in text


def test_current_navigation_links_the_engine_choice_guide() -> None:
    assert "Choosing-the-Prediction-Engine" in _read("wiki/_Sidebar.md")
    assert "competition-scoped engine adr" in _read("docs/INDEX.md").lower()
