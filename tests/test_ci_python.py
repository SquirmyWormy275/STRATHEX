"""Disposable CI copies must not retain the shared tool cache's write access."""

import os
import stat
import struct
import subprocess
import sys

import pytest

from scripts.prepare_ci_python import copy_installation, private_shell_environment


@pytest.mark.skipif(os.name != "posix", reason="POSIX modes; native CI exercises Windows ownership")
def test_copy_tightens_only_disposable_installation_and_preserves_executability(tmp_path):
    source = tmp_path / "shared-cache"
    source.mkdir(mode=0o777)
    binary = source / "bin"
    binary.mkdir(mode=0o777)
    executable = binary / "python3"
    executable.write_bytes(b"reviewed runner executable")
    library = source / "runtime.py"
    library.write_text("reviewed = True\n")
    for path in (source, binary, executable, library):
        path.chmod(0o777 if path != library else 0o666)
    (binary / "python").symlink_to("python3")
    private = tmp_path / "private"
    private.mkdir(mode=0o700)

    copied = copy_installation(source, private)

    assert stat.S_IMODE(private.stat().st_mode) == 0o700
    assert stat.S_IMODE(copied.stat().st_mode) == 0o700
    assert stat.S_IMODE((copied / "bin").stat().st_mode) == 0o700
    assert stat.S_IMODE((copied / "bin/python3").stat().st_mode) == 0o700
    assert stat.S_IMODE((copied / "runtime.py").stat().st_mode) == 0o600
    assert not (copied / "bin/python").is_symlink()
    assert (copied / "bin/python").read_bytes() == executable.read_bytes()
    assert stat.S_IMODE(source.stat().st_mode) == 0o777
    assert stat.S_IMODE(binary.stat().st_mode) == 0o777
    assert stat.S_IMODE(library.stat().st_mode) == 0o666


@pytest.mark.skipif(os.name != "posix", reason="Independent Linux CI shell creation mask")
def test_later_workflow_shell_preserves_private_package_creation(tmp_path):
    startup = private_shell_environment(tmp_path)
    environment = dict(os.environ, BASH_ENV=str(startup))
    previous = os.umask(0o002)
    try:
        subprocess.run(
            ["bash", "--noprofile", "--norc", "-eo", "pipefail", "-c", "mkdir installed; touch installed/module.py"],
            cwd=tmp_path,
            env=environment,
            check=True,
        )
    finally:
        os.umask(previous)
    assert stat.S_IMODE((tmp_path / "installed").stat().st_mode) == 0o700
    assert stat.S_IMODE((tmp_path / "installed/module.py").stat().st_mode) == 0o600


@pytest.mark.skipif(sys.platform != "linux", reason="Linux default POSIX ACL inheritance")
def test_copy_drops_default_acl_before_subsequent_package_installation(tmp_path):
    source = tmp_path / "tool-cache"
    source.mkdir()
    site = source / "site-packages"
    site.mkdir()
    # Linux UAPI posix_acl_xattr: version2, user/group/other rwx entries.
    acl = struct.pack("<I", 2) + b"".join(struct.pack("<HHI", tag, 7, 0xFFFFFFFF) for tag in (1, 4, 32))
    os.setxattr(site, "system.posix_acl_default", acl)
    private = tmp_path / "private"
    private.mkdir(mode=0o700)
    copied = copy_installation(source, private)
    previous = os.umask(0o077)
    try:
        # The source retains its shared cache policy, proving umask alone is
        # insufficient. The disposable copy must not pass that ACL to new code.
        (site / "source-package").mkdir()
        (copied / "site-packages/installed-package").mkdir()
    finally:
        os.umask(previous)
    assert stat.S_IMODE((site / "source-package").stat().st_mode) == 0o777
    assert stat.S_IMODE((copied / "site-packages/installed-package").stat().st_mode) == 0o700
    assert os.getxattr(site, "system.posix_acl_default") == acl
    assert "system.posix_acl_default" not in os.listxattr(copied / "site-packages")
