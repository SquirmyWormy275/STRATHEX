"""Selected runtimes must be protected before any untrusted code can execute."""

import os
import subprocess
import sys
import venv
from pathlib import Path

import pytest
from strathmark.private_storage import private_directory

from woodchopping.runtime_execution import TrustedPython


@pytest.fixture
def runtime(tmp_path):
    private_directory(tmp_path)
    root = tmp_path / "runtime"
    venv.EnvBuilder(with_pip=False, symlinks=os.name != "nt").create(root)
    executable = root / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    site = next(root.glob("lib/python*/site-packages"), root / "Lib/site-packages")
    package = site / "strathmark"
    package.mkdir()
    (package / "__init__.py").write_text("")
    (package / "__main__.py").write_text("import sys\nprint(sys.prefix)\n")
    return root, executable, site


def test_installed_venv_runs_without_resolving_to_base(runtime):
    root, executable, _ = runtime
    guard = TrustedPython(executable)
    assert guard.verify() == executable
    result = subprocess.check_output([str(guard.verify()), "-I", "-m", "strathmark"], text=True)
    assert Path(result.strip()) == root
    guard.verify()  # First import may create cache files, not change the installed source.


@pytest.mark.parametrize("changed", ["interpreter", "configuration", "package", "hook"])
def test_change_after_readiness_is_rejected_before_spawn(runtime, tmp_path, monkeypatch, changed):
    from woodchopping.strathmark_v3_client import V3RuntimeConfigurationError
    from woodchopping.strathmark_v3_local import LocalV3Candidate

    root, executable, site = runtime
    candidate = LocalV3Candidate.__new__(LocalV3Candidate)
    candidate.python, candidate.ml_bundle = executable, tmp_path
    candidate._runtime_guard = TrustedPython(executable)
    if changed == "interpreter":
        executable.unlink()
        executable.write_text("replacement program")
        executable.chmod(0o700)
    elif changed == "configuration":
        with (root / "pyvenv.cfg").open("a") as stream:
            stream.write("\nchanged = yes\n")
    elif changed == "package":
        (site / "strathmark/__main__.py").write_text("raise RuntimeError('substituted package')\n")
    else:
        (site / "injected.pth").write_text("import arbitrary_payload\n")
    monkeypatch.setattr(subprocess, "run", lambda *_a, **_kw: pytest.fail("changed runtime was executed"))
    with pytest.raises(V3RuntimeConfigurationError, match="changed"):
        candidate._run("status")


@pytest.mark.skipif(os.name != "posix", reason="POSIX permissions; native ACLs are enforced on Windows")
@pytest.mark.parametrize("where", ["ancestor", "interpreter", "package", "hook"])
def test_shared_runtime_rejected_before_managed_execution(runtime, tmp_path, monkeypatch, where):
    from woodchopping.managed_launcher import run_cli

    root, executable, site = runtime
    # Do not chmod the base interpreter reached through the venv's symlink.
    if where == "interpreter":
        import shutil

        target = executable.resolve()
        executable.unlink()
        shutil.copyfile(target, executable)
        selected = executable
    elif where == "ancestor":
        selected = root
    elif where == "package":
        selected = site / "strathmark/__main__.py"
    else:
        selected = site / "shared.pth"
        selected.write_text("import arbitrary_payload\n")
    selected.chmod(0o777)
    monkeypatch.setattr(subprocess, "run", lambda *_a, **_kw: pytest.fail("shared runtime was executed"))
    with pytest.raises((PermissionError, ValueError), match="(another account|replaceable|shared)"):
        run_cli(executable, ["capabilities"])
    assert selected.stat().st_mode & 0o777 == 0o777


def test_linux_command_rechecks_interpreter_after_readiness(runtime, tmp_path, monkeypatch):
    from woodchopping.strathmark_v3_client import V3RuntimeConfigurationError
    from woodchopping.strathmark_v3_linux import LinuxV3Competition

    _, executable, site = runtime
    candidate = LinuxV3Competition.__new__(LinuxV3Competition)
    candidate.python = executable
    candidate._runtime_guard = TrustedPython(executable)
    (site / "strathmark/__main__.py").write_text("raise RuntimeError('substituted package')\n")
    monkeypatch.setattr(subprocess, "run", lambda *_a, **_kw: pytest.fail("changed Linux runtime executed"))
    with pytest.raises(V3RuntimeConfigurationError, match="changed"):
        candidate._run("settle", {})


def test_base_python_cannot_be_mistaken_for_separate_installed_environment():
    with pytest.raises(ValueError, match="separately installed"):
        TrustedPython(Path(sys.executable).resolve())


def test_managed_cli_executes_only_selected_installed_environment(runtime, capfd):
    from woodchopping.managed_launcher import run_cli

    root, executable, _ = runtime
    assert run_cli(executable, ["capabilities"]) == 0
    assert Path(capfd.readouterr().out.strip()) == root
