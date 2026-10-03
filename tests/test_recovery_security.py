import hashlib
import json
import shutil
import subprocess
import tarfile
import tempfile
import threading
from pathlib import Path

import pytest

from scripts.recovery_security import (
    encrypt_file,
    load_policy,
    plaintext_sha,
    tar_digests,
    verify_file,
)


@pytest.fixture
def gpg_archive(tmp_path):
    binary = shutil.which("gpg")
    if binary is None or not Path("/dev/shm").is_dir():
        pytest.skip("native GPG and independent temporary filesystem are required")
    home = tmp_path / "gpg"
    home.mkdir(mode=0o700)
    base = [
        binary,
        "--homedir",
        str(home),
        "--batch",
        "--pinentry-mode",
        "loopback",
        "--passphrase",
        "",
    ]
    subprocess.run(
        base + ["--quick-generate-key", "STRATH synthetic test", "ed25519", "cert", "0"],
        check=True,
        capture_output=True,
    )
    listed = subprocess.check_output(base + ["--with-colons", "--list-keys"], stderr=subprocess.DEVNULL).decode()
    fingerprint = next(line.split(":")[9] for line in listed.splitlines() if line.startswith("fpr:"))
    subprocess.run(
        base + ["--quick-add-key", fingerprint, "cv25519", "encr", "0"],
        check=True,
        capture_output=True,
    )
    policy = tmp_path / "policy.json"
    policy.write_text(
        json.dumps(
            {
                "schema_version": "strath-recovery-encryption-policy-v1",
                "gpg_binary": binary,
                "gpg_binary_sha256": hashlib.sha256(Path(binary).read_bytes()).hexdigest(),
                "gpg_home": str(home),
                "recipient_fingerprint": fingerprint,
            }
        )
    )
    source = tmp_path / "synthetic.tar.gz"
    data = tmp_path / "synthetic-key.txt"
    data.write_bytes(b"synthetic signing-key bytes; no production data")
    with tarfile.open(source, "w:gz") as archive:
        archive.add(data, arcname="installation/synthetic-key.txt")
    with tempfile.TemporaryDirectory(prefix="strath-gpg-test-", dir="/dev/shm") as directory:
        if Path(directory).stat().st_dev == home.stat().st_dev:
            pytest.skip("test requires independent temporary filesystems")
        yield source, Path(directory) / "backup.tar.gz.gpg", policy
    subprocess.run(["gpgconf", "--homedir", str(home), "--kill", "gpg-agent"], capture_output=True)


def test_native_encrypt_decrypt_and_complete_member_readback(gpg_archive):
    source, destination, policy = gpg_archive
    original = source.read_bytes()
    result = encrypt_file(source, destination, policy)
    assert result["authenticated_decryption_readback"] is True
    assert result["plaintext_sha256"] == hashlib.sha256(original).hexdigest()
    assert source.read_bytes() == original
    assert verify_file(destination, policy) == result
    assert tar_digests(destination, policy) == {
        "installation/synthetic-key.txt": hashlib.sha256(b"synthetic signing-key bytes; no production data").hexdigest()
    }
    assert destination.stat().st_mode & 0o077 == 0


def test_ciphertext_tampering_and_repeat_output_are_refused(gpg_archive):
    source, destination, policy = gpg_archive
    encrypt_file(source, destination, policy)
    original = destination.read_bytes()
    with pytest.raises(FileExistsError):
        encrypt_file(source, destination, policy)
    assert destination.read_bytes() == original
    destination.write_bytes(original[:-10] + b"corruption")
    with pytest.raises(ValueError, match="ciphertext checksum"):
        verify_file(destination, policy)


def test_private_key_and_archive_cannot_share_filesystem(gpg_archive):
    source, _, policy = gpg_archive
    with pytest.raises(ValueError, match="different filesystems"):
        encrypt_file(source, source.parent / "same-filesystem.gpg", policy)


def test_bulk_streaming_and_truncated_authenticated_tail(gpg_archive):
    source, destination, policy = gpg_archive
    # More than either OS pipe's capacity; small fixtures cannot expose deadlock.
    source.write_bytes(b"synthetic archive input\x00" * 200000)
    expected = hashlib.sha256(source.read_bytes()).hexdigest()
    encrypt_file(source, destination, policy)
    configured = load_policy(policy)
    assert plaintext_sha(destination, configured) == expected
    destination.write_bytes(destination.read_bytes()[:-12])
    # Bypass the receipt checksum deliberately to exercise GPG's own end check.
    with pytest.raises(ValueError, match="authenticated GPG"):
        plaintext_sha(destination, configured)
    assert not [t for t in threading.enumerate() if t.name == "strath-gpg-input"]


def test_early_gpg_exit_preserves_source_and_joins_feeder(gpg_archive):
    source, destination, policy = gpg_archive
    source.write_bytes(b"synthetic oversized pipe input" * 200000)
    original = hashlib.sha256(source.read_bytes()).hexdigest()
    configured = json.loads(policy.read_text())
    configured["recipient_fingerprint"] = "A" * 40
    policy.write_text(json.dumps(configured))
    with pytest.raises(ValueError, match="authenticated GPG"):
        encrypt_file(source, destination, policy)
    assert not destination.exists()
    assert hashlib.sha256(source.read_bytes()).hexdigest() == original
    assert not [t for t in threading.enumerate() if t.name == "strath-gpg-input"]


def test_tar_failure_closes_gpg_and_feeder(gpg_archive, tmp_path):
    source, destination, policy = gpg_archive
    linked = tmp_path / "unsafe-link"
    linked.symlink_to("../outside")
    with tarfile.open(source, "w:gz") as archive:
        archive.add(linked, arcname="unsafe-link")
    encrypt_file(source, destination, policy)
    with pytest.raises(ValueError, match="unsafe members"):
        tar_digests(destination, policy)
    assert not [t for t in threading.enumerate() if t.name == "strath-gpg-input"]
