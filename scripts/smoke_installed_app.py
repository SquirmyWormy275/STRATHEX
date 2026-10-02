"""Install an exact wheel and drive the terminal app against synthetic data."""

from __future__ import annotations

import argparse
import os
import subprocess
import tempfile
import venv
from pathlib import Path

from openpyxl import Workbook


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wheel", type=Path, required=True)
    args = parser.parse_args()
    wheel = args.wheel.resolve(strict=True)
    with tempfile.TemporaryDirectory(prefix="strathex-installed-") as temporary:
        root = Path(temporary)
        environment = root / "environment"
        venv.EnvBuilder(with_pip=True).create(environment)
        python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        subprocess.run(
            [str(python), "-m", "pip", "install", "--disable-pip-version-check", str(wheel)], check=True, timeout=300
        )
        workbook = Workbook()
        workbook.remove(workbook.active)
        workbook.create_sheet("Competitor").append(["CompetitorID", "Name", "Country", "State/Province", "Gender"])
        workbook.create_sheet("wood").append(
            [
                "Scientific Name",
                "species",
                "speciesID",
                "country",
                "region",
                "janka_hard",
                "spec_gravity",
                "crush_strength",
                "shear",
                "MOR",
                "MOE",
            ]
        )
        workbook.create_sheet("Results").append(
            ["competitor_name", "event", "raw_time", "species", "size_mm", "quality", "date"]
        )
        workbook_path = root / "synthetic.xlsx"
        workbook.save(workbook_path)
        workbook.close()
        child_env = {
            key: value for key, value in os.environ.items() if not key.startswith(("STRATHMARK_", "STRATHEX_"))
        }
        child_env.update(STRATHMARK_TEST_DB="1", PYTHONUTF8="1")
        completed = subprocess.run(
            [str(python), "-m", "strathex_cli", "--workbook", str(workbook_path), "--data-dir", str(root / "data")],
            input="9\nn\n",
            cwd=root,
            env=child_env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=60,
        )
        if completed.returncode or "Goodbye!" not in completed.stdout:
            raise RuntimeError(completed.stdout + completed.stderr)
        print("Installed STRATHEX started and exited successfully with synthetic data outside the checkout.")


if __name__ == "__main__":
    main()
