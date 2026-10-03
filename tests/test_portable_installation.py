import json
import tarfile
import tempfile
from pathlib import Path

import pytest

pytest.importorskip("fcntl", reason="the standalone installer is a separate Linux profile")
from scripts.install_portable import activate, atomic_json, identifier, installation_lock, read_json, verify_bundle


def test_corrupt_release_refused_before_profile_or_active_changes(tmp_path):
    bundle = tmp_path / "release"
    bundle.mkdir()
    (bundle / "package.whl").write_bytes(b"corrupt wheel")
    atomic_json(
        bundle / "release.json",
        {
            "schema_version": "strath-portable-release-v1",
            "python": "3.13",
            "release_id": "synthetic-1",
            "files": {"package.whl": {"sha256": "a" * 64, "bytes": 13, "roles": ["app", "runtime"]}},
        },
    )
    with pytest.raises(ValueError, match="checksum"):
        verify_bundle(bundle)
    assert not (tmp_path / "active.json").exists()


def test_profile_switch_and_rollback_preserve_keys_saved_scope_and_archive(tmp_path):
    home = tmp_path / "installation"
    home.mkdir()
    with tempfile.TemporaryDirectory(dir="/dev/shm", prefix="strath-rollback-") as directory:
        backup = Path(directory)
        if backup.stat().st_dev == home.stat().st_dev:
            pytest.skip("an independent filesystem is required for this recovery test")
        workbook = tmp_path / "synthetic.xlsx"
        workbook.write_bytes(b"synthetic workbook")
        for release in ("synthetic-1", "synthetic-2"):
            root = home / "profiles" / release
            root.mkdir(parents=True)
            interpreter = root / "python"
            interpreter.write_bytes(b"synthetic interpreter")
            data = {
                "state": "verified",
                "release_id": release,
                "app_python": str(interpreter),
                "runtime_python": str(interpreter),
                "workbook": str(workbook),
                "backup_dir": str(backup),
                "data_dir": str(root / "data"),
                "runtime_root": str(root / "authority"),
            }
            atomic_json(root / "profile.json", data)
        old = home / "profiles/synthetic-1"
        (old / "authority").mkdir()
        key = old / "authority/private-key"
        key.write_bytes(b"irreplaceable synthetic signing key")
        (old / "data").mkdir()
        saved = old / "data/saved-competition.json"
        saved.write_bytes(b'{"source_identity":"original-exact-source"}')
        with installation_lock(home):
            activate(home, "synthetic-1")
            activate(home, "synthetic-2")
            assert json.loads((home / "active.json").read_text())["previous"] == "synthetic-1"
            activate(home, "synthetic-1")
        assert key.read_bytes() == b"irreplaceable synthetic signing key"
        assert saved.read_bytes() == b'{"source_identity":"original-exact-source"}'
        active = json.loads((home / "active.json").read_text())
        assert active["release_id"] == "synthetic-1"
        with tarfile.open(active["recovery_archive"]) as archive:
            assert (
                archive.extractfile("installation/profiles/synthetic-1/authority/private-key").read()
                == key.read_bytes()
            )


def test_adopted_external_authority_is_in_the_independent_archive(tmp_path):
    home = tmp_path / "installation"
    home.mkdir()
    authority = tmp_path / "old-authority"
    authority.mkdir()
    (authority / "owner-key").write_bytes(b"old-profile-key")
    data = tmp_path / "old-data"
    data.mkdir()
    (data / "saved.json").write_bytes(b"immutable-competition")
    workbook = tmp_path / "synthetic.xlsx"
    workbook.write_bytes(b"synthetic")
    interpreter = tmp_path / "python"
    interpreter.write_bytes(b"synthetic")
    with tempfile.TemporaryDirectory(dir="/dev/shm", prefix="strath-adopt-") as directory:
        backup = Path(directory)
        atomic_json(
            home / "profiles/old/profile.json",
            dict(
                state="verified",
                release_id="old",
                app_python=str(interpreter),
                runtime_python=str(interpreter),
                workbook=str(workbook),
                backup_dir=str(backup),
                data_dir=str(data),
                runtime_root=str(authority),
            ),
        )
        selected = activate(home, "old")
        assert selected["runtime_root"] == str(authority)
        archive_path = read_json(home / "active.json")["recovery_archive"]
        with tarfile.open(archive_path) as archive:
            assert archive.extractfile("retained-profiles/old/runtime_root/owner-key").read() == b"old-profile-key"
            assert archive.extractfile("retained-profiles/old/data_dir/saved.json").read() == b"immutable-competition"


@pytest.mark.parametrize("release", ["../escape", "/absolute", "name/child", ""])
def test_profile_names_cannot_escape_installation(release):
    with pytest.raises(ValueError):
        identifier(release)
