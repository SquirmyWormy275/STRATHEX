import hashlib
import json
import os
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
    install,
    installation_lock,
    launch,
    read_json,
    recovery_archive,
    require_atomic_archive_publication,
    require_independent,
    sha,
    verified_bundle_snapshot,
    verify_bundle,
    verify_content_identity,
)


def _synthetic_bundle(tmp_path):
    bundle = tmp_path / "release"
    bundle.mkdir()
    payload = b"reviewed immutable wheel bytes"
    (bundle / "package.whl").write_bytes(payload)
    atomic_json(
        bundle / "release.json",
        {
            "schema_version": "strath-portable-release-v1",
            "python": "3.13",
            "release_id": "synthetic-verified",
            "v2_source_commit": V2_SOURCE_COMMIT,
            "v2_source_digest": V2_SOURCE_DIGEST,
            "files": {
                "package.whl": {
                    "sha256": hashlib.sha256(payload).hexdigest(),
                    "bytes": len(payload),
                    "roles": ["app", "runtime"],
                }
            },
        },
    )
    return bundle, payload


def test_verified_private_snapshot_survives_source_replacement(tmp_path):
    bundle, payload = _synthetic_bundle(tmp_path)
    home = tmp_path / "installation"
    previous = os.umask(0)
    try:
        with verified_bundle_snapshot(home, bundle) as (snapshot, manifest):
            (bundle / "package.whl").write_bytes(b"attacker replacement")
            assert (snapshot / "package.whl").read_bytes() == payload
            assert snapshot.stat().st_mode & 0o777 == 0o700
            assert (snapshot / "package.whl").stat().st_mode & 0o777 == 0o600
            assert verify_bundle(snapshot) == manifest
        assert not snapshot.exists()
    finally:
        os.umask(previous)


@pytest.mark.parametrize("replacement", ["contents", "symlink"])
def test_replacement_after_initial_verification_never_reaches_uv(tmp_path, monkeypatch, replacement):
    from scripts import install_portable

    bundle, _ = _synthetic_bundle(tmp_path)
    verify = install_portable.verify_bundle
    victim = tmp_path / "victim"
    victim.write_bytes(b"unrelated private bytes")

    def racing_verify(path):
        manifest = verify(path)
        target = path / "package.whl"
        if replacement == "symlink":
            target.unlink()
            target.symlink_to(victim)
        else:
            target.write_bytes(b"substituted executable bytes")
        return manifest

    monkeypatch.setattr(install_portable, "verify_bundle", racing_verify)
    monkeypatch.setattr(subprocess, "run", lambda *_args, **_kwargs: pytest.fail("unverified bytes reached uv"))
    with pytest.raises((ValueError, OSError)):
        install(tmp_path / "installation", bundle, tmp_path / "workbook", tmp_path / "backup", "uv", stage_only=True)
    assert not (tmp_path / "installation/profiles").exists()
    assert not list((tmp_path / "installation").glob(".verified-bundle-*"))
    assert victim.read_bytes() == b"unrelated private bytes"


def test_shared_installation_home_is_rejected_without_chmod(tmp_path):
    bundle, _ = _synthetic_bundle(tmp_path)
    home = tmp_path / "shared"
    home.mkdir()
    home.chmod(0o777)
    with pytest.raises(PermissionError, match="owner-controlled"):
        with verified_bundle_snapshot(home, bundle):
            pytest.fail("peer-writable staging accepted")
    assert home.stat().st_mode & 0o777 == 0o777
    assert list(home.iterdir()) == []


def test_installation_lock_does_not_follow_existing_symlink(tmp_path):
    home = tmp_path / "installation"
    home.mkdir(mode=0o700)
    victim = tmp_path / "victim"
    victim.write_bytes(b"unchanged")
    before = victim.stat().st_mode
    (home / ".profile.lock").symlink_to(victim)
    with pytest.raises(OSError):
        with installation_lock(home):
            pytest.fail("symlink lock accepted")
    assert victim.read_bytes() == b"unchanged"
    assert victim.stat().st_mode == before


def test_profile_archive_uses_local_inventory_for_large_saved_file(tmp_path):
    from scripts.recovery_security import MAX_MEMBER_BYTES

    home = tmp_path / "installation"
    data = home / "data"
    data.mkdir(parents=True)
    retained = data / "synthetic-large-history.bin"
    with retained.open("wb") as stream:
        stream.truncate(MAX_MEMBER_BYTES + 512)
    workbook = tmp_path / "synthetic.xlsx"
    workbook.write_bytes(b"synthetic workbook")
    with tempfile.TemporaryDirectory(dir="/dev/shm", prefix="strath-large-recovery-") as directory:
        backup = Path(directory)
        if backup.stat().st_dev == home.stat().st_dev:
            pytest.skip("an independent filesystem is required for this recovery test")
        archive = Path(recovery_archive(home, backup, workbook))
        receipt = read_json(archive.with_suffix(".verified.json"))
        assert receipt["files"] == {
            "installation/data/synthetic-large-history.bin": sha(retained),
            "operator-workbook.xlsx": sha(workbook),
        }
        assert retained.stat().st_size == MAX_MEMBER_BYTES + 512
        assert not (home / "active.json").exists()


def test_profile_archive_rejects_writer_name_change_before_selection(tmp_path, monkeypatch):
    home = tmp_path / "installation"
    home.mkdir()
    workbook = tmp_path / "synthetic.xlsx"
    workbook.write_bytes(b"irreplaceable synthetic workbook")
    original = workbook.read_bytes()
    add = tarfile.TarFile.add

    def altered(archive, name, arcname=None, **kwargs):
        return add(archive, name, arcname="unexpected-name", **kwargs)

    monkeypatch.setattr(tarfile.TarFile, "add", altered)
    with tempfile.TemporaryDirectory(dir="/dev/shm", prefix="strath-changed-recovery-") as directory:
        backup = Path(directory)
        if backup.stat().st_dev == home.stat().st_dev:
            pytest.skip("an independent filesystem is required for this recovery test")
        with pytest.raises(ValueError, match="trusted inventory"):
            recovery_archive(home, backup, workbook)
        assert list(backup.glob("*.tar.gz"))
        assert not list(backup.glob("*.verified.json"))
    assert workbook.read_bytes() == original
    assert not (home / "active.json").exists()


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

            from scripts.recovery_security import inspect_file

            inspection = inspect_file(archive_path, home / "recovery-encryption-policy.json")
            assert inspection["verification_scope"] == "integrity_only"
            assert inspection["origin_authenticated"] is False
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


def test_encrypted_portable_profile_keeps_retro_flags_out_of_managed_cli(tmp_path, monkeypatch):
    import sys

    import scripts.install_portable as installer
    import strathex_cli
    from woodchopping import managed_launcher

    selected = dict(
        state="verified",
        app_python="/fixture/app-python",
        runtime_python="/fixture/runtime-python",
        workbook=str(tmp_path / "unused.xlsx"),
        data_dir=str(tmp_path / "data"),
        model=str(tmp_path / "model"),
        runtime_root=str(tmp_path / "runtime"),
        backup_dir=str(tmp_path),
        backup_encryption_supported=True,
    )
    atomic_json(tmp_path / "profiles/test/profile.json", selected)
    atomic_json(tmp_path / "recovery-encryption-policy.json", {"synthetic": "unused by managed mode"})
    monkeypatch.setattr(installer, "verify_content_identity", lambda *_args, **_kwargs: None)
    received = []
    monkeypatch.setattr(
        managed_launcher, "run_cli", lambda interpreter, arguments: received.append((interpreter, list(arguments))) or 0
    )

    def run(command, env):
        monkeypatch.setattr(sys, "argv", ["strathex_cli", *command[4:]])
        with pytest.raises(SystemExit) as stopped:
            strathex_cli.main()
        assert stopped.value.code == 0
        return 0

    monkeypatch.setattr(installer.subprocess, "call", run)
    assert (
        launch(
            tmp_path,
            "test",
            ["--managed-cli-python", "/explicit/component/python", "--managed", "capabilities", "--json"],
        )
        == 0
    )
    assert received == [(Path("/explicit/component/python"), ["capabilities", "--json"])]


@pytest.mark.parametrize("kind", ["shared", "symlink"])
def test_install_refuses_unsafe_profiles_parent_before_uv(tmp_path, monkeypatch, kind):
    bundle, _ = _synthetic_bundle(tmp_path)
    home = tmp_path / "installation"
    home.mkdir(mode=0o755)
    profiles = home / "profiles"
    victim = tmp_path / "unrelated"
    victim.mkdir(mode=0o700)
    retained = victim / "retained-profile"
    retained.write_bytes(b"unchanged original competition")
    if kind == "shared":
        profiles.mkdir(mode=0o777)
        profiles.chmod(0o777)
    else:
        profiles.symlink_to(victim, target_is_directory=True)
    workbook = tmp_path / "workbook.xlsx"
    workbook.write_bytes(b"synthetic workbook")
    monkeypatch.setattr(subprocess, "run", lambda *_a, **_kw: pytest.fail("unsafe profile reached uv"))
    with pytest.raises(PermissionError, match="owner-controlled"):
        install(home, bundle, workbook, tmp_path / "not-mounted", "uv", stage_only=True)
    assert retained.read_bytes() == b"unchanged original competition"
    assert not (profiles / "synthetic-verified").exists()
    assert not (home / "active.json").exists()
    if kind == "shared":
        assert profiles.stat().st_mode & 0o777 == 0o777
    else:
        assert profiles.is_symlink()


def test_install_provisions_private_profiles_parent_before_uv_with_umask_zero(tmp_path, monkeypatch):
    bundle, _ = _synthetic_bundle(tmp_path)
    home = tmp_path / "installation"
    home.mkdir(mode=0o755)
    workbook = tmp_path / "workbook.xlsx"
    workbook.write_bytes(b"synthetic workbook")
    called = []

    def inspect_before_uv(*_args, **_kwargs):
        called.append(True)
        assert (home / "profiles").stat().st_mode & 0o777 == 0o700
        assert (home / "profiles/synthetic-verified").stat().st_mode & 0o777 == 0o700
        raise RuntimeError("stop the synthetic installer after checking its private destination")

    monkeypatch.setattr(subprocess, "run", inspect_before_uv)
    previous = os.umask(0)
    try:
        with pytest.raises(RuntimeError, match="synthetic installer"):
            install(home, bundle, workbook, tmp_path / "not-mounted", "uv", stage_only=True)
    finally:
        os.umask(previous)
    assert called == [True]
    assert home.stat().st_mode & 0o777 == 0o755
    assert not (home / "active.json").exists()


def test_existing_safe_profile_is_read_without_permission_or_data_changes(tmp_path):
    from scripts.install_portable import profile

    root = tmp_path / "profiles/retained"
    root.mkdir(parents=True, mode=0o700)
    (tmp_path / "profiles").chmod(0o755)
    data = {"release_id": "retained", "state": "verified", "original": "source identity"}
    atomic_json(root / "profile.json", data)
    before = (root.stat().st_mode, (tmp_path / "profiles").stat().st_mode)
    assert profile(tmp_path, "retained") == data
    assert before == (root.stat().st_mode, (tmp_path / "profiles").stat().st_mode)
    (tmp_path / "profiles").chmod(0o777)
    with pytest.raises(PermissionError, match="owner-controlled"):
        profile(tmp_path, "retained")
    assert read_json(root / "profile.json") == data


def test_cli_preserves_home_alias_evidence_before_locking(tmp_path, monkeypatch):
    from scripts import install_portable

    target = tmp_path / "actual-home"
    target.mkdir(mode=0o700)
    alias = tmp_path / "home-alias"
    alias.symlink_to(target, target_is_directory=True)
    monkeypatch.setattr(install_portable.sys, "argv", ["install_portable.py", "--home", str(alias), "list"])
    assert install_portable.main() == 2
    assert list(target.iterdir()) == []
