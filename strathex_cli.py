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
    parser.add_argument(
        "--local-v3-python",
        type=Path,
        help="Separate Python 3.13 environment with the installed V3 Linux numeric candidate",
    )
    parser.add_argument(
        "--local-v3-ml-bundle",
        type=Path,
        help="Verified, trained V3 candidate ML bundle; enables numeric previews only",
    )
    args = parser.parse_args()
    if (args.local_v3_python is None) != (args.local_v3_ml_bundle is None):
        parser.error("--local-v3-python and --local-v3-ml-bundle must be supplied together")
    if args.local_v3_python is not None:
        if args.workbook is None or args.data_dir is None:
            parser.error("local V3 requires an explicit --workbook and --data-dir")
        if not args.local_v3_python.expanduser().is_file() or not args.local_v3_ml_bundle.expanduser().is_dir():
            parser.error("local V3 Python or ML bundle does not exist")
        os.environ["STRATHEX_V3_LOCAL_PYTHON"] = str(args.local_v3_python.expanduser().absolute())
        os.environ["STRATHEX_V3_LOCAL_ML_BUNDLE"] = str(args.local_v3_ml_bundle.expanduser().resolve())
        os.environ["STRATHEX_V3_LOCAL_SNAPSHOTS"] = str(args.data_dir.expanduser().resolve() / "v3-preview-snapshots")
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
