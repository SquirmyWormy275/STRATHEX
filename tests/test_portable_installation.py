import json
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path

import pytest

pytest.importorskip("fcntl", reason="the standalone installer is a separate Linux profile")
from scripts.install_portable import (
    V2_SOURCE_COMMIT,
    V2_SOURCE_DIGEST,
    activate,
    atomic_json,
    identifier,
    installation_lock,
    launch,
    read_json,
    require_atomic_archive_publication,
    require_independent,
    sha,
    verify_bundle,
    verify_content_identity,
)


def test_unsupported_encrypted_archive_filesystem_is_rejected_without_residue(tmp_path, monkeypatch):
    import errno

    def unsupported(*_args):
        raise OSError(errno.EOPNOTSUPP, "hard links unavailable")

    monkeypatch.setattr("scripts.install_portable.os.link", unsupported)
    with pytest.raises(ValueError, match="no archive was started"):
        require_atomic_archive_publication(tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_encrypted_archive_publication_probe_cleans_up(tmp_path):
    require_atomic_archive_publication(tmp_path)
    assert list(tmp_path.iterdir()) == []


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
            "v2_source_commit": V2_SOURCE_COMMIT,
            "v2_source_digest": V2_SOURCE_DIGEST,
            "files": {"package.whl": {"sha256": "a" * 64, "bytes": 13, "roles": ["app", "runtime"]}},
        },
    )
    with pytest.raises(ValueError, match="checksum"):
        verify_bundle(bundle)
    assert not (tmp_path / "active.json").exists()


@pytest.mark.parametrize("encrypted", [False, True])
def test_profile_switch_and_rollback_preserve_keys_saved_scope_and_archive(tmp_path, encrypted):
    home = tmp_path / "installation"
    home.mkdir()
    if encrypted:
        binary = shutil.which("gpg")
        if binary is None:
            pytest.skip("native GPG required")
        key_home = tmp_path / "gpg"
        key_home.mkdir(mode=0o700)
        command = [binary, "--homedir", str(key_home), "--batch", "--pinentry-mode", "loopback", "--passphrase", ""]
        subprocess.run(
            command + ["--quick-generate-key", "STRATH synthetic test", "ed25519", "cert", "0"],
            check=True,
            capture_output=True,
        )
        listing = subprocess.check_output(
            command + ["--with-colons", "--list-keys"], stderr=subprocess.DEVNULL
        ).decode()
        fingerprint = next(line.split(":")[9] for line in listing.splitlines() if line.startswith("fpr:"))
        subprocess.run(
            command + ["--quick-add-key", fingerprint, "cv25519", "encr", "0"], check=True, capture_output=True
        )
        atomic_json(
            home / "recovery-encryption-policy.json",
            dict(
                schema_version="strath-recovery-encryption-policy-v1",
                gpg_binary=binary,
                gpg_binary_sha256=sha(Path(binary)),
                gpg_home=str(key_home),
                recipient_fingerprint=fingerprint,
            ),
        )
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
            unchanged = (home / "active.json").read_bytes()
            activate(home, "synthetic-2")
            assert (home / "active.json").read_bytes() == unchanged
            activate(home, "synthetic-1")
        assert key.read_bytes() == b"irreplaceable synthetic signing key"
        assert saved.read_bytes() == b'{"source_identity":"original-exact-source"}'
        active = json.loads((home / "active.json").read_text())
        assert active["release_id"] == "synthetic-1"
        archive_path = Path(active["recovery_archive"])
        if encrypted:
            import io

            from scripts.recovery_security import verify_file

            verify_file(archive_path, home / "recovery-encryption-policy.json")
            assert archive_path.name.endswith(".tar.gz.gpg")
            assert not list(backup.glob("*.tar.gz"))
            raw = subprocess.run(command + ["--decrypt", str(archive_path)], check=True, capture_output=True).stdout
            archive_stream = tarfile.open(fileobj=io.BytesIO(raw), mode="r:gz")
        else:
            archive_stream = tarfile.open(archive_path)
        with archive_stream as archive:
            assert (
                sum(
                    archive.extractfile(item).read() == key.read_bytes()
                    for item in archive.getmembers()
                    if item.isfile()
                )
                == 1
            )
            assert (
                archive.extractfile("installation/profiles/synthetic-1/authority/private-key").read()
                == key.read_bytes()
            )
        assert Path(active["recovery_archive"]).stat().st_mode & 0o777 == 0o600
    if encrypted:
        subprocess.run(["gpgconf", "--homedir", str(key_home), "--kill", "gpg-agent"], capture_output=True)


def test_workbook_and_backup_same_filesystem_refused(tmp_path):
    with tempfile.TemporaryDirectory(dir="/dev/shm") as directory:
        backup = Path(directory)
        workbook = backup / "workbook.xlsx"
        workbook.write_bytes(b"synthetic")
        with pytest.raises(ValueError, match="workbook"):
            require_independent(tmp_path, backup, workbook)


@pytest.mark.parametrize("field", ["v2_source_commit", "v2_source_digest"])
def test_frozen_v2_identity_mandatory(tmp_path, field):
    manifest = dict(
        schema_version="strath-portable-release-v1",
        python="3.13",
        v2_source_commit=V2_SOURCE_COMMIT,
        v2_source_digest=V2_SOURCE_DIGEST,
    )
    manifest.pop(field)
    atomic_json(tmp_path / "release.json", manifest)
    with pytest.raises(ValueError, match="frozen V2"):
        verify_bundle(tmp_path)


@pytest.mark.parametrize(
    "runtime,arguments",
    [
        (False, ["--workbook=elsewhere.xlsx"]),
        (False, ["--local-v3-p", "/tmp/python"]),
        (False, ["--data", "/tmp/data"]),
        (True, ["status", "--runtime-root", "/tmp/root"]),
        (True, ["status", "--ml-b=other"]),
    ],
)
def test_managed_launch_paths_cannot_be_overridden(tmp_path, runtime, arguments):
    atomic_json(tmp_path / "profiles/test/profile.json", dict(state="verified", backup_dir=str(tmp_path)))
    with pytest.raises(ValueError, match="overridden"):
        launch(tmp_path, "test", arguments, runtime=runtime)


def test_modified_program_or_model_block_launch_but_missing_model_allows_recovery(tmp_path):
    program = tmp_path / "program.py"
    program.write_bytes(b"original program")
    model = tmp_path / "model"
    model.mkdir()
    weights = model / "weights.json"
    weights.write_bytes(b"original model")
    selected = dict(
        app_python=str(program), runtime_python=str(program), model=str(model), runtime_root=str(tmp_path / "authority")
    )
    selected["content_identity"] = dict(
        schema_version="strath-portable-content-identity-v1",
        profile_paths=selected.copy(),
        core_files={str(program): sha(program)},
        core_roots={},
        model_files={"weights.json": sha(weights)},
    )
    verify_content_identity(selected)
    weights.write_bytes(b"changed model")
    with pytest.raises(ValueError, match="model"):
        verify_content_identity(selected, allow_missing_model=True)
    weights.unlink()
    with pytest.raises(ValueError, match="model"):
        verify_content_identity(selected)
    verify_content_identity(selected, allow_missing_model=True)
    program.write_bytes(b"changed program")
    with pytest.raises(ValueError, match="program"):
        verify_content_identity(selected, allow_missing_model=True)


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
