"""Copy the CI-provisioned Python into a private, disposable runner installation.

Hosted tool caches can have shared writable ancestors. Exercise production runtime
checks with a separate protected installation; never relax the application guard
or change permissions on the shared runner cache.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

IDENTITY_PROBE = """
import encodings, json, pathlib, sys, sysconfig
maps = pathlib.Path('/proc/self/maps')
libraries = sorted({line.split(maxsplit=5)[-1].strip()
                    for line in maps.read_text().splitlines()
                    if '/libpython' in line}) if maps.exists() else []
print(json.dumps({'prefix': sys.base_prefix, 'version': list(sys.version_info[:2]),
                  'stdlib': encodings.__file__, 'libraries': libraries,
                  'shared': bool(sysconfig.get_config_var('Py_ENABLE_SHARED'))}))
"""


def copy_installation(source, private_root):
    """Keep copied cache modes behind a private parent until tightened."""
    target = private_root / "base"
    # copytree restores the source directory modes, including shared cache
    # permissions. The enclosing fresh private root must never be its target.
    shutil.copytree(source, target, symlinks=False)
    if os.name == "posix":
        removed = 0
        for directory, _, files in os.walk(target):
            removed += private_mode(Path(directory), 0o700)
            for name in files:
                path = Path(directory) / name
                executable = bool(path.stat().st_mode & 0o111)
                removed += private_mode(path, 0o700 if executable else 0o600)
        print(f"Removed {removed} copied POSIX access/default ACLs from the disposable installation.")
    return target


def private_mode(path, mode):
    """Drop copied ACL inheritance only on newly owned disposable CI paths."""
    removed = 0
    if sys.platform == "linux":
        # copytree also copies ACL xattrs. A default ACL overrides the umask
        # for future pip-created children, even after chmod protects the parent.
        for name in os.listxattr(path):
            if name in {"system.posix_acl_access", "system.posix_acl_default"}:
                os.removexattr(path, name)
                removed += 1
    path.chmod(mode)
    return removed


def private_shell_environment(private_root):
    """Carry the private creation mask into later independent Linux CI steps."""
    startup = private_root / "ci-shell.sh"
    startup.write_text("umask 077\n", encoding="utf-8")
    startup.chmod(0o600)
    return startup


def main():
    if os.environ.get("GITHUB_ACTIONS") != "true":
        raise RuntimeError("This provisioning helper is only for disposable GitHub CI runners")
    incoming_mask = os.umask(0o077)
    if sys.platform == "linux":
        print(f"Runner shell creation mask was {incoming_mask:03o}; private CI steps require 077.")
    source = Path(sys.base_prefix)
    private_root = Path.home() / (".strathex-ci-python-" + uuid4().hex)
    private_root.mkdir(mode=0o700)
    if os.name == "posix":
        private_mode(private_root, 0o700)
    # Dereference the reviewed runner image's links while copying, so the new
    # installation never returns to a mutable shared tool-cache directory.
    target = copy_installation(source, private_root)
    executable = target / ("python.exe" if os.name == "nt" else "bin/python3")
    environment = os.environ.copy()
    if sys.platform == "linux":
        # setup-python's shared interpreter can retain the tool cache in its
        # library search path. Never send its old LD_LIBRARY_PATH to this copy.
        environment["LD_LIBRARY_PATH"] = str(target / "lib")
        environment.pop("LD_PRELOAD", None)
    observed = json.loads(
        subprocess.check_output(
            [str(executable), "-I", "-c", IDENTITY_PROBE],
            text=True,
            env=environment,
        )
    )
    if Path(observed["prefix"]).resolve() != target.resolve() or observed["version"] != [3, 13]:
        raise RuntimeError("Copied CI Python did not retain its separate installation identity")
    if not Path(observed["stdlib"]).resolve().is_relative_to(target.resolve()):
        raise RuntimeError("Copied CI Python still imports the original standard library")
    if sys.platform == "linux":
        if observed["shared"] and not observed["libraries"]:
            raise RuntimeError("Cannot verify the copied Python's loaded shared library")
        if any(not Path(path).resolve().is_relative_to(target.resolve()) for path in observed["libraries"]):
            raise RuntimeError("Copied CI Python still loads a shared library outside its private installation")
    print(json.dumps(observed, sort_keys=True))
    with Path(os.environ["GITHUB_PATH"]).open("a", encoding="utf-8") as stream:
        stream.write(str(executable.parent) + "\n")
        if os.name == "nt":
            stream.write(str(target / "Scripts") + "\n")
    environments = private_root / "environments"
    environments.mkdir(mode=0o700)
    with Path(os.environ["GITHUB_ENV"]).open("a", encoding="utf-8") as stream:
        stream.write("STRATHEX_CI_PYTHON=" + executable.as_posix() + "\n")
        stream.write("STRATHEX_CI_ENV_ROOT=" + environments.as_posix() + "\n")
        if sys.platform == "linux":
            stream.write("LD_LIBRARY_PATH=" + str(target / "lib") + "\nLD_PRELOAD=\n")
            stream.write("BASH_ENV=" + str(private_shell_environment(private_root)) + "\n")
    print("Prepared separate private Python 3.13 for disposable CI environments.")


if __name__ == "__main__":
    main()
