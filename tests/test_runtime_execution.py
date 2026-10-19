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


@pytest.mark.skipif(os.name != "posix", reason="Shared ELF/Mach-O base library protection")
@pytest.mark.parametrize("change", ["writable", "bytes", "link"])
def test_shared_base_library_is_checked_before_guarded_spawn(runtime, tmp_path, monkeypatch, change):
    from woodchopping.managed_launcher import run_cli

    root, executable, _ = runtime
    base = tmp_path / "base"
    (base / "bin").mkdir(parents=True, mode=0o700)
    (base / "lib").mkdir(mode=0o700)
    library = base / "lib/libpython3.13.so.1.0"
    library.write_bytes(b"original synthetic library")
    link = library.with_name("libpython3.13.so")
    link.symlink_to(library.name)
    config = root / "pyvenv.cfg"
    lines = config.read_text().splitlines()
    config.write_text("\n".join("home = " + str(base / "bin") if row.startswith("home =") else row for row in lines))
    guard = TrustedPython(executable)
    assert str(library) in guard.identity
    assert str(link) in guard.identity
    monkeypatch.setattr(subprocess, "run", lambda *_a, **_kw: pytest.fail("changed base library was executed"))
    if change == "writable":
        library.chmod(0o666)
        with pytest.raises(PermissionError, match="another account"):
            run_cli(executable, ["capabilities"])
    else:
        if change == "bytes":
            library.write_bytes(b"substituted library bytes")
        else:
            replacement = library.with_name("replacement.so")
            replacement.write_bytes(library.read_bytes())
            link.unlink()
            link.symlink_to(replacement.name)
        with pytest.raises(ValueError, match="changed"):
            guard.verify()


@pytest.mark.skipif(os.name != "nt", reason="Native Windows directory ACE semantics")
def test_ancestor_create_child_right_is_distinct_from_importable_directory_write(tmp_path):
    from woodchopping.runtime_execution import _resolved, _trusted

    ancestor = tmp_path / "ancestor"
    private_directory(ancestor)
    environment = {key: value for key, value in os.environ.items() if key.upper() != "PSMODULEPATH"}
    environment["CI_ANCESTOR_PATH"] = str(ancestor)
    environment["CI_ACCESS_RIGHT"] = "CreateDirectories"
    command = r"""
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$path = $env:CI_ANCESTOR_PATH
$acl = Get-Acl -LiteralPath $path
$sid = [System.Security.Principal.SecurityIdentifier]::new('S-1-5-11')
$rule = [System.Security.AccessControl.FileSystemAccessRule]::new(
    $sid, [System.Security.AccessControl.FileSystemRights]$env:CI_ACCESS_RIGHT,
    [System.Security.AccessControl.AccessControlType]::Allow)
$acl.AddAccessRule($rule)
Set-Acl -LiteralPath $path -AclObject $acl
"""
    subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command], check=True, env=environment
    )
    _trusted(ancestor, directory=True, ancestor=True)
    with pytest.raises(PermissionError, match="replaceable"):
        _trusted(ancestor, directory=True)
    # A final regular file is a tool input, never a directory ancestor. It must
    # pass the real Windows file API and still reject another account's writes.
    final = ancestor / "runtime.py"
    final.write_text("reviewed = True\n")
    assert _resolved(final, {}) == final
    environment.update(CI_ANCESTOR_PATH=str(final), CI_ACCESS_RIGHT="WriteData")
    subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command], check=True, env=environment
    )
    with pytest.raises(PermissionError, match="replaceable"):
        _resolved(final, {})
