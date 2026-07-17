"""Adapter date-hygiene tests.

build_competitor_records() must never hand a pandas ``NaT`` across the boundary
to STRATHMARK. STRATHMARK treats only ``None`` as "no date"; a ``NaT`` slips past
its ``result_date is not None`` filter and then crashes its date sort with
``TypeError: Cannot compare NaT with datetime.date object``.
"""

from datetime import date

import pandas as pd

from woodchopping.strathmark_adapter import build_competitor_records


def _df_with_mixed_dates():
    """A competitor with some valid dates and one blank (-> NaT in a datetime column)."""
    return pd.DataFrame(
        {
            "competitor_name": ["Al Axe"] * 4,
            "event": ["SB"] * 4,
            "raw_time": [30.0, 31.0, 29.0, 32.0],
            "species": ["S01"] * 4,
            "size_mm": [300.0] * 4,
            "quality": [5] * 4,
            # datetime64 column with a NaT (blank Excel cell after to_datetime)
            "date": pd.to_datetime(["2024-01-01", "2024-02-01", None, "2024-03-01"]),
            "heat_id": ["H1"] * 4,
        }
    )


def test_no_nat_result_dates_leak_across_boundary():
    records = build_competitor_records(["Al Axe"], _df_with_mixed_dates())
    assert len(records) == 1

    history = records[0].history
    assert history, "expected historical results to be built"

    for h in history:
        # result_date must be either a real date or None — never NaT/NaN.
        assert h.result_date is None or isinstance(h.result_date, date), f"bad result_date type: {h.result_date!r}"
        assert not (h.result_date is not None and pd.isna(h.result_date)), "NaT leaked into result_date"


def test_valid_dates_are_preserved():
    records = build_competitor_records(["Al Axe"], _df_with_mixed_dates())
    dated = [h.result_date for h in records[0].history if h.result_date is not None]
    # The three real dates survive as datetime.date; the blank becomes None.
    assert date(2024, 1, 1) in dated
    assert date(2024, 3, 1) in dated
    assert len(dated) == 3


def test_history_is_sortable_by_result_date():
    """The exact operation strathmark performs must not raise."""
    records = build_competitor_records(["Al Axe"], _df_with_mixed_dates())
    dated = [h for h in records[0].history if h.result_date is not None]
    # Mirrors strathmark._apply_form_trajectory's sort key.
    ordered = sorted(dated, key=lambda r: r.result_date)
    assert [r.result_date for r in ordered] == sorted(r.result_date for r in dated)
