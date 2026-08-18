# -*- coding: utf-8 -*-
"""
Handicap fairness assessment -- STRATHMARK compatibility wrapper.

Public STRATHEX function signatures are retained.  Engine calls pass through
``woodchopping.strathmark_adapter`` so the adapter remains the single
STRATHMARK dependency boundary.
"""

from __future__ import annotations

import textwrap
from typing import Any, Dict, List, Optional

from woodchopping.strathmark_adapter import (
    get_ai_assessment_engine,
    get_championship_analysis_engine,
    simulate_and_assess_engine,
)


def get_ai_assessment_of_handicaps(analysis: Dict[str, Any]) -> str:
    """Return STRATHMARK's LLM/statistical fairness assessment."""
    return get_ai_assessment_engine(analysis)


def get_championship_race_analysis(
    analysis: Dict[str, Any],
    predictions: List[Dict],
) -> str:
    """Return STRATHMARK's championship race analysis."""
    return get_championship_analysis_engine(analysis, predictions)


def simulate_and_assess_handicaps(
    competitors_with_marks: List[Dict[str, Any]],
    num_simulations: Optional[int] = None,
) -> None:
    """
    Run the established Monte Carlo, display, and fairness-assessment workflow.

    The return value remains ``None`` because existing STRATHEX callers use this
    function for its console output.
    """
    simulate_and_assess_engine(
        competitors_with_marks,
        num_simulations=num_simulations,
        show=True,
    )


def format_ai_assessment(assessment: str, width: int = 100) -> None:
    """
    Print an AI assessment with stable plain-text wrapping.

    This restores the formatter imported by the existing comprehensive
    prediction-analysis screen.  It changes presentation only: headings,
    paragraph order, and assessment text are preserved.
    """
    text = "" if assessment is None else str(assessment)
    width = max(40, int(width))

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()

        if not stripped:
            print()
            continue

        # Preserve compact headings and divider lines exactly.
        if len(stripped) <= width and (
            stripped.isupper() or set(stripped) <= {"-", "=", "_"} or stripped.endswith(":")
        ):
            print(stripped)
            continue

        initial_indent = line[: len(line) - len(line.lstrip())]
        subsequent_indent = initial_indent

        for marker in ("- ", "* ", "+ "):
            if stripped.startswith(marker):
                initial_indent += marker
                subsequent_indent += " " * len(marker)
                stripped = stripped[len(marker) :]
                break

        wrapped = textwrap.fill(
            stripped,
            width=width,
            initial_indent=initial_indent,
            subsequent_indent=subsequent_indent,
            break_long_words=False,
            break_on_hyphens=False,
        )
        print(wrapped)
