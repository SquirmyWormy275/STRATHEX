"""Guard tests: the app must never mint a partial (Competitor-only) workbook.

Regression coverage for the bug where a missing ``woodchopping.xlsx`` was
silently recreated with only an empty ``Competitor`` sheet (no ``Wood`` /
``Results``), which shadowed the real data and broke wood-species selection.

Every test isolates the Excel path to a per-test ``tmp_path`` by monkeypatching
``excel_io.paths`` — these tests NEVER read or write the production workbook.
"""

import os
from types import SimpleNamespace

import pytest
from openpyxl import Workbook, load_workbook

import woodchopping.data.excel_io as excel_io


@pytest.fixture
def isolated_paths(tmp_path, monkeypatch):
    """Redirect excel_io's view of the workbook to a throwaway tmp file."""
    fake = SimpleNamespace(
        EXCEL_FILE=str(tmp_path / "woodchopping.xlsx"),
        COMPETITOR_SHEET="Competitor",
        WOOD_SHEET="wood",
        RESULTS_SHEET="Results",
    )
    monkeypatch.setattr(excel_io, "paths", fake)
    return fake, tmp_path


def _write_canonical_seed(path):
    """Create a woodchopping_clean.xlsx with all three sheets + a data row each."""
    wb = Workbook()
    wb.remove(wb["Sheet"])
    ws = wb.create_sheet("Wood")
    ws.append(excel_io.WOOD_HEADERS)
    ws.append(
        [
            "Pinus strobus",
            "eastern white pine",
            "S01",
            "USA",
            "east",
            380,
            0.35,
            1,
            1,
            1,
            1,
        ]
    )
    ws = wb.create_sheet("Competitor")
    ws.append(excel_io.COMPETITOR_HEADERS)
    ws.append(["C001", "Alice", "AUS", "NSW", "F"])
    ws = wb.create_sheet("Results")
    ws.append(
        [
            "CompetitorID",
            "Event",
            "Time (seconds)",
            "Size (mm)",
            "Species Code",
            "Quality",
            "HeatID",
            "Date",
        ]
    )
    wb.save(path)
    wb.close()


def _sheet_names_lower(path):
    wb = load_workbook(path)
    names = [s.lower() for s in wb.sheetnames]
    wb.close()
    return names


def test_load_competitors_df_missing_file_creates_no_stub(isolated_paths):
    """A read of a missing workbook must NOT create any file (no silent stub)."""
    fake, _ = isolated_paths
    assert not os.path.exists(fake.EXCEL_FILE)

    df = excel_io.load_competitors_df()

    assert not os.path.exists(fake.EXCEL_FILE), "load_competitors_df must not create a workbook"
    assert list(df.columns) == ["competitor_name", "competitor_country"]
    assert df.empty


def test_ensure_workbook_restores_from_canonical_seed(isolated_paths):
    """When woodchopping_clean.xlsx exists, ensure_workbook restores full data."""
    fake, tmp = isolated_paths
    _write_canonical_seed(os.path.join(tmp, "woodchopping_clean.xlsx"))

    excel_io.ensure_workbook()

    assert os.path.exists(fake.EXCEL_FILE)
    names = _sheet_names_lower(fake.EXCEL_FILE)
    assert {"wood", "competitor", "results"} <= set(names)
    # Seeded data (not just headers) carried across.
    wb = load_workbook(fake.EXCEL_FILE)
    assert wb["Competitor"].max_row >= 2
    wb.close()


def test_ensure_workbook_builds_full_skeleton_without_seed(isolated_paths):
    """No seed available -> a COMPLETE skeleton, never a Competitor-only file."""
    fake, _ = isolated_paths

    excel_io.ensure_workbook()

    assert os.path.exists(fake.EXCEL_FILE)
    names = _sheet_names_lower(fake.EXCEL_FILE)
    assert "wood" in names, "skeleton must include a Wood sheet (never Competitor-only)"
    assert "competitor" in names
    assert "results" in names


def test_ensure_workbook_is_noop_when_file_present(isolated_paths):
    """An existing workbook must not be overwritten."""
    fake, tmp = isolated_paths
    _write_canonical_seed(os.path.join(tmp, "woodchopping_clean.xlsx"))
    # Pre-create the target with a marker sheet.
    wb = Workbook()
    wb.remove(wb["Sheet"])
    wb.create_sheet("Sentinel")
    wb.save(fake.EXCEL_FILE)
    wb.close()

    excel_io.ensure_workbook()

    assert "sentinel" in _sheet_names_lower(fake.EXCEL_FILE), "existing workbook must be left untouched"


def test_wood_data_readable_after_guard(isolated_paths):
    """The guard's workbook must expose the columns the wood menu needs."""
    fake, _ = isolated_paths
    excel_io.ensure_workbook()

    df = excel_io.load_wood_data()

    assert "species" in df.columns and "speciesID" in df.columns
