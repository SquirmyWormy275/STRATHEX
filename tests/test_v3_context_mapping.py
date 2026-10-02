"""Operator event codes must reach the V3 assessor in its canonical vocabulary."""

from types import SimpleNamespace

import pandas as pd
import pytest

from woodchopping.ui.handicap_ui import _build_engine_request


@pytest.mark.parametrize(
    ("operator_code", "canonical_code"),
    [("UH", "underhand"), ("SB", "standing_block")],
)
def test_operator_event_code_is_canonical_in_v3_context(operator_code, canonical_code):
    request = _build_engine_request(
        context=SimpleNamespace(scope_id="tournament:context-test"),
        field_local_id="heat:one",
        competitors_df=pd.DataFrame({"competitor_id": ["C01"], "competitor_name": ["Test"]}),
        wood_species="pine",
        wood_diameter=300,
        wood_quality=5,
        event_code=operator_code,
        results_df=pd.DataFrame(),
        upstream_field_revision=1,
        numeric_options={"requested_at_utc": "2026-10-02T16:00:00.000Z"},
    )

    assert request["target_context"]["event_code"] == canonical_code
    assert request["event_code"] == operator_code
