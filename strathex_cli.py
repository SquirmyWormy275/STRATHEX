"""Portable launcher that selects operator paths before application imports."""

from __future__ import annotations

import argparse
import os
import runpy
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Run STRATHEX with a selected workbook and data directory.")
    parser.add_argument("--workbook", type=Path, help="Existing workbook with Competitor, Wood, and Results sheets")
    parser.add_argument("--data-dir", type=Path, help="Directory for saves, authority, commands, and ResultStore")
    args = parser.parse_args()
    if args.workbook is not None:
        workbook = args.workbook.expanduser().resolve()
        if not workbook.is_file():
            parser.error(f"workbook does not exist: {workbook}")
        os.environ["STRATHEX_WORKBOOK"] = str(workbook)
    if args.data_dir is not None:
        directory = args.data_dir.expanduser().resolve()
        directory.mkdir(parents=True, exist_ok=True)
        os.environ.setdefault("STRATHMARK_DB_PATH", str(directory / "results.db"))
        os.environ.setdefault("STRATHEX_PREDICTION_AUTHORITY_DB", str(directory / "prediction_authority.db"))
        os.environ.setdefault("STRATHEX_V3_COMMAND_DB", str(directory / "v3_commands.db"))
        os.chdir(directory)
    runpy.run_module("MainProgramV5_2", run_name="__main__")


if __name__ == "__main__":
    main()
