"""Release-version and wheel-selection contract checks."""

from __future__ import annotations

import tomllib
from pathlib import Path

import woodchopping


def test_hatch_derives_package_version_from_one_canonical_source():
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["project"]["dynamic"] == ["version"]
    assert pyproject["tool"]["hatch"]["version"]["path"] == "woodchopping/__init__.py"
    assert woodchopping.__version__ == "6.0.1"


def test_wheel_includes_package_and_required_top_level_config():
    pyproject = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))

    assert pyproject["tool"]["hatch"]["build"]["targets"]["wheel"]["only-include"] == [
        "woodchopping",
        "config.py",
    ]


def test_compatibility_launcher_displays_canonical_version():
    launcher = Path("MainProgramV5_2.py").read_text(encoding="utf-8")

    assert "from woodchopping import __version__ as STRATHEX_VERSION" in launcher
    assert "CALCULATOR v{STRATHEX_VERSION}" in launcher
