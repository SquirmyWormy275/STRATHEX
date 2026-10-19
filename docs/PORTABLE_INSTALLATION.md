# Portable Linux installations and rollback

STRATHEX 7.4 supplies `scripts/install_portable.py`, a standard-library Linux bootstrap. A private release bundle contains `release.json`, complete SHA256-pinned wheel sets for two Python 3.13 environments, and the operator's exact Formula/ML candidate. Models and workbook history stay outside the public repository and GitHub releases. The public installer does not contain trained weights or operator data.

New 7.4.6 app environments use the reviewed STRATHMARK 3.0.0rc14 security source pinned in `pyproject.toml` and the installer. The package retains the V2 numerical engine and its `2.0.0` calculation contract. The runtime environment contains the separately reviewed V3 wheel. Installation copies every checked file into an exclusive private snapshot, hashes those exact opened bytes before provisioning, uses only that snapshot with offline wheels and no dependency resolution, and verifies installed runtime/model/Formula identities and package versions. New profiles use separate saved-data and signing-authority directories. Installation errors leave the previous active profile selected.

The security upgrade changes the default source for new installations and newly selected V2 roots. It does not rewrite saved root receipts, issued marks, history, or the old `a231ad65fe82317516cc82a282761d73adb0c0e3` source identity in retained profiles. Resume an existing immutable Linux V3 competition using its original profile, interpreter, model, keys and backups. New private bundles must carry the installer's current `V2_SOURCE_COMMIT` and `V2_SOURCE_DIGEST`; an old bundle is not accepted as a new release. The digest is computed from the exact installed wheel's Python sources, and fixed-cutoff direct/HTTP parity must pass before changing either pin.

On Windows, a new or empty dedicated `--data-dir` is provisioned privately before the application opens its databases. An existing nonempty directory is checked without changing its permissions. Broader shared access or writable ancestry stops startup; provision a reviewed private application directory instead. Do not select the home root, source checkout or workbook directory as the data directory. Existing saved files are never moved or rewritten to repair permissions. Installed-app CI starts and restarts the real application on both operating systems and checks that its synthetic history stays unchanged.

```bash
python3 scripts/install_portable.py install \
  --bundle /private/strath-release \
  --manifest-sha256 TRUSTED_RELEASE_MANIFEST_SHA256 \
  --workbook /operator/woodchopping.xlsx \
  --backup-dir /independent-disk/recovery \
  --uv /path/to/uv
python3 scripts/install_portable.py list
python3 scripts/install_portable.py launch
python3 scripts/install_portable.py runtime -- status
python3 scripts/install_portable.py rollback
python3 scripts/install_portable.py activate strathex-7.4.2-strathmark-3.0.0rc7-recovery-final
```

The installation home defaults to `~/.local/share/strath/installations`; use `--home /private/location` before the operation to choose another. Selection and rollback first create an independent archive of profile descriptors, workbooks, saved competitions, command outboxes and signing-authority files. Every regular member is read back and checked against its source SHA256, and a dated verification record explains the change. Adopted profiles retain their original paths; their external data and authority directories are included too. The backup location must be on a different filesystem from both the installation and every retained workbook or authority. Archives are created with owner-only mode 0600 from their first byte on filesystems that support POSIX permissions; removable filesystems such as some NTFS mounts may not enforce that mode, so their physical/access permissions determine confidentiality. Never discard the exact old environments, trained model, signing keys or saved data after upgrading.

The launcher holds a profile lock for the application's entire lifetime. Close STRATHEX before changing the active profile. To resume an older saved competition, launch its original profile explicitly:

```bash
python3 scripts/install_portable.py launch --profile linux-competition-7.3.2
```

Rollback selects the previous verified profile. It preserves later profiles and their competition history. It does not downgrade or rewrite a competition under another source identity. Both V2 and V3 remain deliberate per-competition choices. An existing competition never changes its selected engine because the active installation changes.

The install command requires the SHA256 of the exact `release.json` bytes from a separately protected, reviewed private-bundle build record. It checks that identity before parsing the manifest or installing any wheels. Never derive this argument from the selected bundle or its adjacent checksums: a replacement supplier can change both. Acquire the bootstrap itself through the reviewed release; its embedded `RECOVERY_HELPER_SHA256` authenticates its paired helper before executing those exact checked bytes. These checks establish the supplied trusted artifact identity, not a new signing authority.

Before making a new installation the normal launcher, verify the actual installed app outside a checkout, the engine selector, the full approval/issue/results/restart workflow, and a restored independent backup. The release bundle's SHA256 list verifies bytes; it is not a digital signature or a grant of Windows CNG qualification. Obtain the installer and release manifest from the reviewed release, and keep private bundle backups independently.

Every launch rechecks the recorded interpreter, V2/app/V3 program files, import hooks, Formula, signing identity and model bytes. Profile-managed paths cannot be replaced by trailing command arguments. A missing inference model blocks new forecasts; explicit retained lifecycle operations and result corrections may continue with unchanged authority and source identity. Changing present model bytes is always refused. Selecting the already active profile preserves its previous rollback target.

## 7.4.1 encrypted recovery support

The retained rc6 private profile is `strathex-7.4.1-strathmark-3.0.0rc6-release-reviewed`. Keep previous profiles for saved competitions; their exact source bindings cannot be upgraded in place. The bootstrap ships with a release-matched, standalone `recovery_security.py` companion. An optional private `recovery-encryption-policy.json` in the installation home enables GPG-encrypted profile-switch archives and, for profiles declaring `backup_encryption_supported`, native competition backups. The policy format and authenticated recovery checks are documented in the [STRATHMARK Linux runbook](https://github.com/SquirmyWormy275/STRATHMARK/blob/main/docs/V3_LINUX_COMPETITION.md). A policy never upgrades retained older binaries: their native archives use their original format. Preserve plaintext legacy archives until encryption readback and an independent protected recovery-key copy are verified. Public wheels and installer assets contain no keys, workbook results or trained weights.

`install --stage-only` provisions and verifies a new profile without changing the active selection. It can retain the intended archive path while the drive is unavailable; activation and launch still enforce the independent-backup prerequisite. Use `activate RELEASE_ID` after the drive is recognized. Staging is not proof of a durable backup.

Encrypted archives publish through a locked private temporary file. Full authenticated readback finishes before the final ciphertext appears; interrupted publication can be retried without overwriting a completed archive. The verification receipt alone is not a completed backup or proof of its producer. Use the independent content check described below before treating a later archive as trusted recovery evidence.

Encrypted recovery requires hard-link support for atomic publication without overwriting an existing archive. The bootstrap checks this capability before staging an activation/rollback archive and before launching an encrypted competition profile. Filesystems without hard links, including exFAT, are rejected before an archive starts. Use an independent filesystem that passes the check.

## 7.4.2 buffered recovery

The new profile is `strathex-7.4.2-strathmark-3.0.0rc7-recovery-final`. The helper uses bounded bulk input/output through GPG pipes, avoiding tiny direct filesystem operations on large removable-drive archives. Complete authenticated readback and no-overwrite publication are unchanged. Retained rc6 competitions use their exact old runtime; the rc6 prospective protocol also requires that original implementation. New profiles cannot silently replace either identity. See [7.4.2 release notes](RELEASE_v7.4.2.md).

## 7.4.4 bounded archive verification

Keep both public bootstrap scripts from the same release beside each other, including for plaintext backups. The new recovery helper is a self-contained standard-library port of STRATHMARK's bounded archive policy; it is not byte-identical to the installed STRATHMARK module. Its standalone reader permits at most 64 MiB per file, 128 MiB of expanded archive bytes and 1,024 members, with a 30-second processing deadline. It rejects unsafe paths, duplicate names, links, special files and sparse files. TAR extension records are limited to 16 KiB each and bounded in number before their contents are parsed.

Profile selection and rollback can preserve larger existing snapshots. Before creating the archive, the installer records the exact names, file sizes and SHA256 hashes from local source files. Both plaintext and encrypted readback use that caller-owned inventory: every archived file must have the expected name and size, every expected file must be present, and final hashes must agree with unchanged source files. The expansion allowance includes only those sizes, block padding and 32 KiB per file plus 32 KiB for TAR overhead. Archive headers cannot increase it. The processing deadline is 30 seconds plus one second per MiB of source data, capped at six hours; checks occur between bounded reads and do not cancel a stalled operating-system read.

These checks change verification, not the saved archive format or retained profile identity. Encryption still requires complete authenticated GPG readback. Failure leaves the active profile and source files unchanged and does not delete the rejected archive. Preserve old recovery helpers and exact old runtimes with their profiles; use the new release's bootstrap pair for new profile selection. A large archive without a trusted local inventory must not be granted a larger budget using sizes supplied by the archive itself.


## 7.4.5 independent recovery identity

A holder of the public recovery key can encrypt chosen content and write matching
unsigned receipt hashes. Successful authenticated decryption therefore proves
ciphertext integrity, not the backup's origin. Later standalone `verify` calls now
require `--expected-plaintext-sha256` from an independently protected plaintext
identity. Keep that value from the trusted source archive or a protected creation
record; never copy it from the archive's adjacent `.verified.json`. A matching pin
identifies that exact content, not a signer, a claimed installation label or the
latest recovery point. Verify the intended competition/recovery point independently
and retain the same content check on the actual decryption used for restoration.

For example, use `python recovery_security.py verify --policy /private/policy.json --source /independent/backup.tar.gz.gpg --expected-plaintext-sha256 TRUSTED_SHA256`.
Without an independent identity, `inspect` remains available for legacy forensic
inspection and reports `verification_scope: integrity_only` and
`origin_authenticated: false`. It must not authorize recovery by itself. `verify`
reports `trusted_plaintext_identity` after checking the independent pin; it does not
claim a sender signature. The archive and receipt schema, existing certification-only
keys, encryption subkeys and private policies remain unchanged. Archives lacking a
trusted pin remain decryptable; obtain independent source/inventory evidence before
using them for recovery rather than inventing an identity from their receipts.

The GPG input must be a regular file without a final symlink; its ciphertext hash
and decryption consume the same opened descriptor. Receipt inputs are likewise
bounded regular files. The default plaintext-container allowance is 128 MiB, with a
ciphertext allowance of twice that amount plus 1 MiB. A receipt's plaintext byte
count must be an integer within the caller's allowance and match actual decryption;
it can never increase a budget. `--max-plaintext-bytes` accepts a larger independently
known source/inventory allowance up to 1 TiB. Creation derives its limit from the
opened local source, and installer TAR readback derives its limit from the trusted
inventory described above. Large existing profile backups remain supported without
trusting attacker-declared sizes.

A watchdog kills each GPG process after 30 seconds plus one second per MiB of
allowance, capped at six hours, including when the GPG output pipe is blocked.
An operating-system read stalled on the source drive can still delay feeder cleanup
until the OS returns; bounded TAR checks likewise do not cancel a stalled OS read.
The new checks preserve source files and rejected archives, retain permissive
removable-drive ciphertext storage, and do not change saved profile source identities.
Keep the new installer and standalone helper paired with their release, and retain
historical helpers/runtimes with their original profiles.


Installation and profile-parent directories must have trusted ownership and no peer
write access; existing unsafe directories and symlink aliases stop without changing
their permissions. Missing dedicated directories are created with mode 0700 regardless
of umask. New profile directories are never substituted for old ones, and failed staging
does not change the active profile. Preserve the original 7.4.4/rc12 and 7.4.2/rc7
profiles and their identities when provisioning 7.4.6/rc14.


## Selected runtime execution

Managed CLI, local preview and Linux competition clients require a separately
installed Python virtual environment. Keep its interpreter, base Python, package
files and import hooks under trusted ownership without peer write access. A
shared runtime is rejected before it executes; the client never changes those
folders' permissions. Ordinary protected venv and uv interpreter symlinks remain
supported, and execution keeps the venv path so its own packages are selected.
Environments inheriting system site packages are rejected.

The client records the interpreter/link, configuration, installed-package and
standard-library file identities before its first call, and rechecks them before
each later call. Changing the selected installation stops that client; reopen its
original profile rather than updating a running competition's runtime. Generated
Python caches may appear, but their access permissions are still checked. This
protects against another account replacing a runtime and detects changed owner
installations between calls; it does not authenticate an initially malicious
runtime deliberately installed by the operator. Use reviewed artifacts for new
installations. Retained rc7, rc12 and rc13 profiles keep their original source,
model, signing keys and saved competitions.
