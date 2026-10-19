"""Disposable CI copies must not retain the shared tool cache's write access."""

import os
import stat

import pytest

from scripts.prepare_ci_python import copy_installation


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
