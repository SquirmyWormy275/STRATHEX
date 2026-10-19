import gzip
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
from pathlib import Path

import pytest

from scripts import recovery_security
from scripts.recovery_security import (
    encrypt_file,
    inspect_file,
    load_policy,
    plaintext_sha,
    tar_digests,
    tar_stream_digests,
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


@pytest.mark.parametrize("archive_mode", [0o700, 0o777])
def test_native_encrypt_decrypt_and_complete_member_readback(gpg_archive, archive_mode):
    source, destination, policy = gpg_archive
    destination.parent.chmod(archive_mode)
    original = source.read_bytes()
    result = encrypt_file(source, destination, policy)
    assert result["authenticated_decryption_readback"] is True
    assert result["plaintext_sha256"] == hashlib.sha256(original).hexdigest()
    assert source.read_bytes() == original
    checked = verify_file(
        destination, policy, expected_plaintext_sha256=hashlib.sha256(source.read_bytes()).hexdigest()
    )
    assert checked["verification_scope"] == "trusted_plaintext_identity"
    assert checked["untrusted_receipt"] == result
    assert tar_digests(destination, policy) == {
        "installation/synthetic-key.txt": hashlib.sha256(b"synthetic signing-key bytes; no production data").hexdigest()
    }
    assert tar_digests(
        destination,
        policy,
        expected_sizes={"installation/synthetic-key.txt": len(b"synthetic signing-key bytes; no production data")},
    ) == tar_digests(destination, policy)
    with pytest.raises(ValueError, match="trusted inventory"):
        tar_digests(destination, policy, expected_sizes={"installation/synthetic-key.txt": 1})
    assert destination.stat().st_mode & 0o077 == 0


def test_ciphertext_tampering_and_repeat_output_are_refused(gpg_archive):
    source, destination, policy = gpg_archive
    encrypt_file(source, destination, policy)
    original = destination.read_bytes()
    with pytest.raises(FileExistsError):
        encrypt_file(source, destination, policy)
    assert destination.read_bytes() == original
    destination.write_bytes(original[:-10] + b"corruption")
    with pytest.raises(ValueError, match="ciphertext checksum|authenticated GPG"):
        verify_file(destination, policy, expected_plaintext_sha256=hashlib.sha256(source.read_bytes()).hexdigest())


def test_private_key_and_archive_cannot_share_filesystem(gpg_archive):
    source, _, policy = gpg_archive
    with pytest.raises(ValueError, match="different filesystems"):
        encrypt_file(source, source.parent / "same-filesystem.gpg", policy)


def test_native_gpg_uses_validated_paths_after_aliases_change(gpg_archive, tmp_path):
    source, destination, policy = gpg_archive
    value = json.loads(policy.read_bytes())
    binary_alias, home_alias = tmp_path / "gpg-alias", tmp_path / "home-alias"
    binary_alias.symlink_to(value["gpg_binary"])
    home_alias.symlink_to(value["gpg_home"], target_is_directory=True)
    value.update(gpg_binary=str(binary_alias), gpg_home=str(home_alias))
    policy.write_text(json.dumps(value))
    encrypt_file(source, destination, policy)
    configured = load_policy(policy)
    binary_alias.unlink()
    home_alias.unlink()
    binary_alias.symlink_to(tmp_path / "missing-program")
    home_alias.symlink_to(tmp_path / "missing-key-home", target_is_directory=True)
    assert plaintext_sha(destination, configured) == hashlib.sha256(source.read_bytes()).hexdigest()


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


def archive_bytes(entries):
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:gz") as archive:
        for name, content, kind in entries:
            member = tarfile.TarInfo(name)
            member.type = kind
            member.size = len(content)
            if kind in (tarfile.SYMTYPE, tarfile.LNKTYPE):
                member.linkname = "../outside"
            archive.addfile(member, io.BytesIO(content))
    return output.getvalue()


def test_bounded_reader_preserves_unicode_and_long_pax_names():
    name = "installation/" + "saved-competition-" * 10 + "é.json"
    contents = b"synthetic retained evidence"
    compressed = archive_bytes([(name, contents, tarfile.REGTYPE)])
    expected = {name: hashlib.sha256(contents).hexdigest()}
    assert tar_stream_digests(io.BytesIO(compressed)) == expected
    assert tar_stream_digests(io.BytesIO(compressed), expected_sizes={name: len(contents)}) == expected


def test_declared_member_limit_rejected_before_missing_payload_is_read():
    member = tarfile.TarInfo("oversized")
    member.size = recovery_security.MAX_MEMBER_BYTES + 1
    compressed = gzip.compress(member.tobuf() + b"\0" * 1024)
    with pytest.raises(ValueError, match="member budget"):
        tar_stream_digests(io.BytesIO(compressed))


def test_default_member_count_includes_directories():
    compressed = archive_bytes(
        [(f"directory-{i}", b"", tarfile.DIRTYPE) for i in range(recovery_security.MAX_ARCHIVE_MEMBERS + 1)]
    )
    with pytest.raises(ValueError, match="member budget"):
        tar_stream_digests(io.BytesIO(compressed))


def test_expansion_bomb_and_trailing_expansion_are_bounded(monkeypatch):
    monkeypatch.setattr(recovery_security, "MAX_EXPANDED_BYTES", 65536)
    compressed = archive_bytes([("large", b"\0" * 100000, tarfile.REGTYPE)])
    with pytest.raises(ValueError, match="expanded-byte budget"):
        tar_stream_digests(io.BytesIO(compressed))
    valid = archive_bytes([("small", b"small", tarfile.REGTYPE)])
    # A second gzip member after tar's end blocks must consume the same budget.
    with pytest.raises(ValueError, match="expanded-byte budget"):
        tar_stream_digests(io.BytesIO(valid + gzip.compress(b"\0" * 100000)))


@pytest.mark.parametrize("kind", [tarfile.XHDTYPE, tarfile.XGLTYPE, tarfile.GNUTYPE_LONGNAME])
def test_metadata_size_is_bounded_even_for_large_trusted_inventory(kind):
    member = tarfile.TarInfo("metadata")
    member.type = kind
    member.size = recovery_security.MAX_TAR_METADATA_BYTES + 1
    compressed = gzip.compress(member.tobuf() + b"\0" * 1024)
    with pytest.raises(ValueError, match="metadata budget"):
        tar_stream_digests(io.BytesIO(compressed), expected_sizes={"huge": 21 * 1024**3})


def test_chained_metadata_and_sparse_block_maps_are_refused():
    longname = tarfile.TarInfo("longname")
    longname.type = tarfile.GNUTYPE_LONGNAME
    longname.size = 5
    chain = (longname.tobuf() + b"name\0" + b"\0" * 507) * 9
    with pytest.raises(ValueError, match="metadata budget"):
        tar_stream_digests(io.BytesIO(gzip.compress(chain)), expected_sizes={"name": 21 * 1024**3})
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:gz") as archive:
        sparse = tarfile.TarInfo("sparse")
        sparse.pax_headers = {"GNU.sparse.major": "1", "GNU.sparse.minor": "0"}
        sparse.size = 100
        archive.addfile(sparse, io.BytesIO(b"999999999999999999999\n" + b"\0" * 79))
    with pytest.raises(ValueError, match="sparse file"):
        tar_stream_digests(io.BytesIO(output.getvalue()), expected_sizes={"sparse": 21 * 1024**3})


@pytest.mark.parametrize(
    "entries, inventory, error",
    [
        ([("unexpected", b"a", tarfile.REGTYPE)], {"expected": 1}, "trusted inventory"),
        ([("expected", b"ab", tarfile.REGTYPE)], {"expected": 1}, "trusted inventory"),
        ([("expected", b"a", tarfile.REGTYPE)], {"expected": 1, "missing": 0}, "trusted inventory"),
        ([("expected", b"", tarfile.DIRTYPE)], {"expected": 0}, "trusted inventory"),
        ([("same", b"a", tarfile.REGTYPE)] * 2, {"same": 1, "missing": 0}, "repeats a member"),
        ([("../outside", b"", tarfile.REGTYPE)], {"expected": 0}, "unsafe members"),
        ([("/absolute", b"", tarfile.REGTYPE)], {"expected": 0}, "unsafe members"),
        ([("C:/absolute", b"", tarfile.REGTYPE)], {"expected": 0}, "unsafe members"),
        ([("linked", b"", tarfile.SYMTYPE)], {"linked": 0}, "unsafe members"),
        ([("linked", b"", tarfile.LNKTYPE)], {"linked": 0}, "unsafe members"),
    ],
)
def test_exact_local_inventory_rejects_changed_archive(entries, inventory, error):
    with pytest.raises(ValueError, match=error):
        tar_stream_digests(io.BytesIO(archive_bytes(entries)), expected_sizes=inventory)


def test_trusted_inventory_allows_larger_legitimate_snapshot(monkeypatch):
    monkeypatch.setattr(recovery_security, "MAX_MEMBER_BYTES", 32)
    monkeypatch.setattr(recovery_security, "MAX_EXPANDED_BYTES", 32768)
    monkeypatch.setattr(recovery_security, "MAX_ARCHIVE_MEMBERS", 1)
    entries = [(f"saved-{i}", b"evidence" * 10000, tarfile.REGTYPE) for i in range(2)]
    compressed = archive_bytes(entries)
    with pytest.raises(ValueError, match="member budget"):
        tar_stream_digests(io.BytesIO(compressed))
    assert tar_stream_digests(
        io.BytesIO(compressed), expected_sizes={name: len(data) for name, data, _ in entries}
    ) == {name: hashlib.sha256(data).hexdigest() for name, data, _ in entries}


@pytest.mark.parametrize("inventory", [{"../outside": 1}, {"safe": -1}, {"safe": True}])
def test_unusable_caller_inventory_fails_before_stream_read(inventory):
    with pytest.raises(ValueError, match="invalid trusted recovery inventory"):
        tar_stream_digests(io.BytesIO(b"not an archive"), expected_sizes=inventory)


@pytest.mark.parametrize("inventory", [None, {"safe": 0}, {"safe": 100 * 1024**3}])
def test_archive_deadline_is_finite_even_with_large_local_inventory(monkeypatch, inventory):
    now = iter([0, recovery_security.MAX_INVENTORY_DEADLINE_SECONDS + 1])
    monkeypatch.setattr(recovery_security.time, "monotonic", lambda: next(now))
    with pytest.raises(ValueError, match="deadline expired"):
        tar_stream_digests(io.BytesIO(archive_bytes([("safe", b"", tarfile.REGTYPE)])), expected_sizes=inventory)


def test_truncated_gzip_is_refused_after_tar_end_blocks():
    compressed = archive_bytes([("safe", b"data", tarfile.REGTYPE)])
    with pytest.raises(EOFError):
        tar_stream_digests(io.BytesIO(compressed[:-4]))


def test_encrypted_readback_uses_same_bounds_and_preserves_archive(gpg_archive):
    source, destination, policy = gpg_archive
    member = tarfile.TarInfo("oversized")
    member.size = recovery_security.MAX_MEMBER_BYTES + 1
    original = gzip.compress(member.tobuf() + b"\0" * 1024)
    source.write_bytes(original)
    encrypt_file(source, destination, policy)
    encrypted = destination.read_bytes()
    with pytest.raises(ValueError, match="member budget"):
        tar_digests(destination, policy)
    assert source.read_bytes() == original
    assert destination.read_bytes() == encrypted
    assert not [t for t in threading.enumerate() if t.name == "strath-gpg-input"]


def test_helper_runs_without_installed_packages():
    subprocess.run(
        [sys.executable, "-I", "-S", str(Path(recovery_security.__file__)), "--help"],
        check=True,
        capture_output=True,
    )


def _public_only_archive(source, destination, policy, public_home, *, reported_size=None):
    """Model an attacker who knows only the public recipient key and receipt schema."""
    configured = load_policy(policy)
    public_home.mkdir(mode=0o700)
    public_key = subprocess.check_output(
        [
            configured["gpg_binary"],
            "--homedir",
            configured["gpg_home"],
            "--batch",
            "--export",
            configured["recipient_fingerprint"],
        ]
    )
    command = [configured["gpg_binary"], "--homedir", str(public_home), "--batch"]
    subprocess.run(command + ["--import"], input=public_key, check=True, capture_output=True)
    secret_keys = subprocess.check_output(command + ["--with-colons", "--list-secret-keys"], stderr=subprocess.DEVNULL)
    assert b"sec:" not in secret_keys
    subprocess.run(
        command
        + [
            "--trust-model",
            "always",
            "--recipient",
            configured["recipient_fingerprint"],
            "--compress-algo",
            "zlib",
            "--output",
            str(destination),
            "--encrypt",
            str(source),
        ],
        check=True,
        capture_output=True,
    )
    receipt = {
        "schema_version": recovery_security.SCHEMA,
        "recipient_fingerprint": configured["recipient_fingerprint"],
        "ciphertext_sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
        "plaintext_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "plaintext_bytes": source.stat().st_size if reported_size is None else reported_size,
        "source_archive_name": "claimed-genuine-backup.tar.gz",
        "authenticated_decryption_readback": True,
        "original_preserved": True,
    }
    destination.with_name(destination.name + ".verified.json").write_text(json.dumps(receipt))
    subprocess.run(["gpgconf", "--homedir", str(public_home), "--kill", "gpg-agent"], capture_output=True)
    return receipt


def test_public_key_holder_cannot_forge_independently_pinned_recovery(gpg_archive, tmp_path):
    source, destination, policy = gpg_archive
    trusted_identity = hashlib.sha256(source.read_bytes()).hexdigest()
    forged = tmp_path / "chosen-plaintext"
    forged.write_bytes(b"attacker-selected recovery contents")
    _public_only_archive(forged, destination, policy, tmp_path / "public-only")
    result = inspect_file(destination, policy)
    assert result["verification_scope"] == "integrity_only"
    assert result["origin_authenticated"] is False
    with pytest.raises(ValueError, match="independently trusted plaintext identity"):
        verify_file(destination, policy, expected_plaintext_sha256=trusted_identity)
    assert source.exists() and destination.exists()


@pytest.mark.parametrize("pin", [None, "", "a" * 63, "g" * 64, 3, "a" * 64 + "\n"])
def test_missing_or_invalid_trust_pin_fails_before_archive_or_policy_access(tmp_path, pin):
    with pytest.raises(ValueError, match="independently trusted plaintext SHA-256"):
        verify_file(tmp_path / "does-not-exist", tmp_path / "no-policy", expected_plaintext_sha256=pin)


def test_genuine_archive_wrong_identity_is_rejected(gpg_archive):
    source, destination, policy = gpg_archive
    encrypt_file(source, destination, policy)
    with pytest.raises(ValueError, match="independently trusted plaintext identity"):
        verify_file(destination, policy, expected_plaintext_sha256="a" * 64)
    assert (
        verify_file(
            destination, policy, expected_plaintext_sha256=hashlib.sha256(source.read_bytes()).hexdigest().upper()
        )["origin_authenticated"]
        is False
    )


@pytest.mark.parametrize(
    "target,kind",
    [
        ("archive", "symlink"),
        ("archive", "fifo"),
        ("archive", "directory"),
        ("receipt", "symlink"),
        ("receipt", "fifo"),
        ("receipt", "directory"),
    ],
)
def test_nonregular_archive_and_receipt_refused_before_gpg(gpg_archive, monkeypatch, target, kind):
    source, destination, policy = gpg_archive
    encrypt_file(source, destination, policy)
    path = destination if target == "archive" else destination.with_name(destination.name + ".verified.json")
    path.unlink()
    if kind == "symlink":
        path.symlink_to(source)
    elif kind == "fifo":
        os.mkfifo(path)
    else:
        path.mkdir()

    def unexpected(_policy):
        pytest.fail("GPG must not start for a nonregular input")

    monkeypatch.setattr(recovery_security, "_command", unexpected)
    with pytest.raises(ValueError, match="regular file"):
        inspect_file(destination, policy)


def test_oversized_ciphertext_refused_before_process_launch(gpg_archive, monkeypatch):
    source, destination, policy = gpg_archive
    encrypt_file(source, destination, policy)
    maximum = source.stat().st_size
    with destination.open("r+b") as stream:
        stream.truncate(recovery_security._ciphertext_allowance(maximum) + 1)
    monkeypatch.setattr(recovery_security, "_command", lambda _policy: pytest.fail("unexpected GPG"))
    with pytest.raises(ValueError, match="input exceeds byte allowance"):
        inspect_file(destination, policy, max_plaintext_bytes=maximum)


@pytest.mark.parametrize("size", [-1, True, "3", None, 2**50])
def test_receipt_cannot_enlarge_or_corrupt_independent_allowance(gpg_archive, monkeypatch, size):
    source, destination, policy = gpg_archive
    result = encrypt_file(source, destination, policy)
    result["plaintext_bytes"] = size
    destination.with_name(destination.name + ".verified.json").write_text(json.dumps(result))
    monkeypatch.setattr(recovery_security, "_command", lambda _policy: pytest.fail("unexpected GPG"))
    with pytest.raises(ValueError, match="independent byte allowance"):
        inspect_file(destination, policy)


def test_receipt_exact_size_mismatch_rejected(gpg_archive):
    source, destination, policy = gpg_archive
    result = encrypt_file(source, destination, policy)
    result["plaintext_bytes"] -= 1
    destination.with_name(destination.name + ".verified.json").write_text(json.dumps(result))
    with pytest.raises(ValueError, match="checksum or size differs"):
        inspect_file(destination, policy)


def test_gpg_compression_expansion_is_bounded_and_processes_joined(gpg_archive, tmp_path):
    _, destination, policy = gpg_archive
    forged = tmp_path / "compressed-bomb"
    forged.write_bytes(b"x" * (4 * 1024 * 1024))
    _public_only_archive(forged, destination, policy, tmp_path / "public-only", reported_size=1)
    assert destination.stat().st_size < 65536
    with pytest.raises(ValueError, match="output exceeds byte allowance"):
        inspect_file(destination, policy, max_plaintext_bytes=65536)
    assert not [t for t in threading.enumerate() if t.name.startswith("strath-gpg-")]


def test_gpg_deadline_kills_blocked_output_and_joins_threads(gpg_archive, monkeypatch):
    source, _, policy = gpg_archive
    configured = load_policy(policy)
    processes = []
    original = subprocess.Popen

    def launch(*args, **kwargs):
        process = original(*args, **kwargs)
        processes.append(process)
        return process

    monkeypatch.setattr(recovery_security, "_command", lambda _: [sys.executable, "-c", "import time; time.sleep(60)"])
    monkeypatch.setattr(recovery_security.subprocess, "Popen", launch)
    monkeypatch.setattr(recovery_security, "_duration", lambda _: 0.15)
    started = time.monotonic()
    with pytest.raises(ValueError, match="deadline expired"):
        plaintext_sha(source, configured)
    assert time.monotonic() - started < 5
    assert processes and all(process.poll() is not None for process in processes)
    assert not [t for t in threading.enumerate() if t.name.startswith("strath-gpg-")]


def test_ciphertext_digest_and_decryption_use_the_same_open_file(gpg_archive, monkeypatch):
    source, destination, policy = gpg_archive
    encrypt_file(source, destination, policy)
    original = subprocess.Popen
    old_bytes = destination.read_bytes()

    def replace_after_open(*args, **kwargs):
        replacement = destination.with_suffix(".replacement")
        replacement.write_bytes(b"replacement must never be fed to GPG")
        os.replace(replacement, destination)
        return original(*args, **kwargs)

    monkeypatch.setattr(recovery_security.subprocess, "Popen", replace_after_open)
    result = verify_file(destination, policy, expected_plaintext_sha256=hashlib.sha256(source.read_bytes()).hexdigest())
    assert result["untrusted_receipt"]["ciphertext_sha256"] == hashlib.sha256(old_bytes).hexdigest()
    assert destination.read_bytes() == b"replacement must never be fed to GPG"


def test_trusted_large_source_allowance_is_explicit_and_receipt_does_not_supply_it(gpg_archive):
    source, destination, policy = gpg_archive
    source.write_bytes(b"larger than the test's independent allowance" * 10000)
    encrypt_file(source, destination, policy)
    with pytest.raises(ValueError, match="independent byte allowance"):
        inspect_file(destination, policy, max_plaintext_bytes=1024)
    result = verify_file(
        destination,
        policy,
        expected_plaintext_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        max_plaintext_bytes=source.stat().st_size,
    )
    assert result["plaintext_bytes"] == source.stat().st_size


def test_cli_verify_requires_independent_pin_and_inspect_is_explicit(gpg_archive):
    source, destination, policy = gpg_archive
    encrypt_file(source, destination, policy)
    command = [
        sys.executable,
        str(Path(recovery_security.__file__)),
        "verify",
        "--policy",
        str(policy),
        "--source",
        str(destination),
    ]
    missing = subprocess.run(command, capture_output=True, text=True)
    assert missing.returncode == 2 and "independent record" in missing.stderr
    genuine = subprocess.run(
        command + ["--expected-plaintext-sha256", hashlib.sha256(source.read_bytes()).hexdigest()],
        capture_output=True,
        text=True,
        check=True,
    )
    assert json.loads(genuine.stdout)["verification_scope"] == "trusted_plaintext_identity"
    command[2] = "inspect"
    inspected = subprocess.run(command, capture_output=True, text=True, check=True)
    assert json.loads(inspected.stdout)["verification_scope"] == "integrity_only"


def test_input_growth_after_open_cannot_exceed_feeder_budget(tmp_path, monkeypatch):
    source = tmp_path / "growing-input"
    source.write_bytes(b"original")
    original = subprocess.Popen

    def launch(*args, **kwargs):
        with source.open("ab") as stream:
            stream.write(b"x" * 100)
        return original(*args, **kwargs)

    monkeypatch.setattr(recovery_security.subprocess, "Popen", launch)
    monkeypatch.setattr(
        recovery_security,
        "_command",
        lambda _: [sys.executable, "-c", "import sys; sys.stdout.buffer.write(sys.stdin.buffer.read())"],
    )
    with pytest.raises(ValueError, match="input exceeds byte allowance"):
        with recovery_security._gpg_stream(source, {}, [], input_limit=16, output_limit=32, seconds=5) as stream:
            while stream.read(16):
                pass
    assert not [t for t in threading.enumerate() if t.name.startswith("strath-gpg-")]
