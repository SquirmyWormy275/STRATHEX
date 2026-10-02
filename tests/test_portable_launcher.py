"""Launcher validation must precede legacy initialization and preserve venv identity."""

import sys

import pytest

import strathex_cli


@pytest.mark.parametrize(
    "arguments",
    [
        ["--local-v3-python", "/synthetic/python"],
        ["--local-v3-python", "/synthetic/python", "--local-v3-ml-bundle", "/synthetic/model"],
    ],
)
def test_incomplete_local_profile_never_initializes_legacy_app(monkeypatch, arguments):
    monkeypatch.setattr(sys, "argv", ["strathex", *arguments])
    monkeypatch.setattr(
        strathex_cli.runpy, "run_module", lambda *_args, **_kwargs: pytest.fail("legacy initialization")
    )
    with pytest.raises(SystemExit) as error:
        strathex_cli.main()
    assert error.value.code == 2


@pytest.mark.skipif(sys.platform == "win32", reason="Linux venv symlink regression; Windows uses a regular executable")
def test_local_interpreter_symlink_preserved_before_app_import(tmp_path, monkeypatch):
    python = tmp_path / "venv-python"
    python.symlink_to(sys.executable)
    model = tmp_path / "model"
    model.mkdir()
    workbook = tmp_path / "synthetic.xlsx"
    workbook.write_bytes(b"synthetic launcher fixture")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "strathex",
            "--workbook",
            str(workbook),
            "--data-dir",
            str(tmp_path / "data"),
            "--local-v3-python",
            str(python),
            "--local-v3-ml-bundle",
            str(model),
        ],
    )
    for name in (
        "STRATHEX_V3_LOCAL_PYTHON",
        "STRATHEX_V3_LOCAL_ML_BUNDLE",
        "STRATHEX_V3_LOCAL_SNAPSHOTS",
        "STRATHEX_WORKBOOK",
        "STRATHMARK_DB_PATH",
        "STRATHEX_PREDICTION_AUTHORITY_DB",
        "STRATHEX_V3_COMMAND_DB",
    ):
        monkeypatch.setenv(name, "")
        monkeypatch.delenv(name)
    calls = []
    monkeypatch.setattr(strathex_cli.runpy, "run_module", lambda *args, **kwargs: calls.append((args, kwargs)))
    strathex_cli.main()
    assert strathex_cli.os.environ["STRATHEX_V3_LOCAL_PYTHON"] == str(python)
    assert calls == [(("MainProgramV5_2",), {"run_name": "__main__"})]
