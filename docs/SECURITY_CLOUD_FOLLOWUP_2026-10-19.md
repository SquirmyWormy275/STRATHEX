# Security Cloud verification follow-up — STRATHEX 7.4.5

The verification scan of released source `a032031154dd048747bda204267c64450fb1ae71`
reported eight further findings. This follow-up addresses the paths below and pairs
new installations with STRATHMARK 3.0.0rc13. It does not alter handicap mathematics,
the V2 calculation contract, Formula, trained model or the competition's selected
engine. The [initial 7.4.4 repairs](SECURITY_CLOUD_2026-10-19.md) remain in place.

## Findings and resulting behavior

| Finding | Disposition in 7.4.5 |
| --- | --- |
| Imported competition JSON can assert completed rounds and placements | Bind the entire saved byte sequence and path to a digest held in the private installation authority database. Parse the authenticated bytes directly. Modified, historical or unbound files cannot establish their own official state. |
| Portable installer reopens bundle files after verification | Copy and hash the same opened source descriptors into an exclusive private snapshot. Only those checked snapshot files reach wheel installation or model copying. Validate installation/profile ancestry, refuse links or shared write access, and create missing dedicated parents privately before running installation tools. |
| Existing POSIX data directories bypass the private-storage check | Verify existing nonempty directories without changing their modes or files. Direct authority and command-store creation also enforce private storage. Unsafe POSIX and Windows paths stop. |
| Multi-event V2 output can proceed without sheet-bound judge approval | Bind judge approval to the complete sheet and competition context. Check it before day schedules, official export and results; edits and new later-round marks require fresh review. Preserve completed evidence. |
| Linux V3 export writes competitor identifiers as formulas | Write new result strings, including identifiers, as explicit XLSX text cells. Preserve their literal values and keep numeric outcomes numeric. |
| Predictable V3 workbook temporary path follows a symlink | Create an exclusive private temporary file with an unpredictable name, save and sync its open descriptor, verify its identity and the unchanged original workbook, then publish atomically. Refuse unsafe writable ancestry. |
| Managed event IDs can collapse into another same-origin route | Apply the shared canonical event-identifier contract before constructing the workspace URL. Dot segments and alternate route encodings cannot select a different event route. |
| Recovery receipts do not authenticate their producer | Require an independently retained plaintext SHA256 for later `verify`. Offer explicit integrity-only `inspect` for legacy evidence. A public-key-only forgery with a matching unsigned receipt cannot match a different trusted plaintext pin. |

Encrypted verification also rejects nonregular archive/receipt inputs, binds hashing
and decryption to the same opened ciphertext, limits encrypted/decrypted bytes and
kills GPG on its watchdog deadline. Large source archives and profile inventories can
supply a finite independent allowance. Receipt sizes never raise that allowance.
See [portable recovery limits](PORTABLE_INSTALLATION.md#745-independent-recovery-identity).

## Saved competitions and recovery

Keep existing 7.4.4/rc12, 7.4.2/rc7 and other retained profiles with their exact
application, runtime, model, signing key, workbook, saves and private authority
databases. Install 7.4.5/rc13 as a separate profile. A new profile does not enroll
historical JSON, change a competition's engine or migrate its recorded source.
The [adapter](../woodchopping/strathmark_v3_linux.py) and
[installer](../scripts/install_portable.py) carry the exact reviewed identities;
no historical tag, profile manifest or source pin is rewritten.

New save loading requires the exact current byte digest recorded for that original
path. Merely copying the opaque engine-selection reference into another JSON file
cannot authorize its rounds or placements. A missing or changed primary, an unbound
legacy save or a copied backup stops without activating, deleting or rewriting the
primary or backup. The rolling `.bak` remains evidence for reviewed recovery; it is
not automatically promoted. Keep the original private database with the files.

Resume an older competition through its original retained profile where compatible.
If that cannot resume, independently review and recover the complete trusted set;
this release provides no automatic historical-save enrollment or authority reset.
Do not edit JSON, remove database records or initialize replacement keys to bypass
the block. Save publication and the private database update are separate durable
steps: interruption or competing writers between them can produce a mismatch that
also requires review. A restored JSON file alone is insufficient, and changing its
path does not migrate its authority binding. These local protections assume the
operator and machine administrator retain control of the installation/database;
they are not an external monotonic rollback witness.

Private data-directory checks do not silently repair existing shared folders.
Preserve data and independently review the intended private location and access
before changing permissions or moving a profile. Portable staging leaves the active
profile selected; activation still requires a verified independent backup.

## Encryption trust

Existing ciphertext, receipt schemas, certification-only primary keys and encryption
subkeys remain readable. No live key or policy change is required. Authenticated
GPG decryption establishes ciphertext integrity; any holder of the public recipient
key can create a different decryptable archive and matching unsigned hashes.

Obtain a verification pin from the trusted original plaintext or a separately
protected creation record, never from the neighboring receipt. A successful pin
check proves the chosen content identity, not a sender signature or that the chosen
snapshot is the newest. Check the intended competition and recovery point against
independent evidence, and apply the same content check to the actual restoration
stream. Without independent evidence, `inspect` reports `integrity_only` and
`origin_authenticated: false`; it does not authorize a restore. Native competition
backup reuse separately requires exact member hashes from its trusted local snapshot.

Permissive removable ciphertext storage remains supported. GPG's watchdog terminates
the process even during a blocked output-pipe read; a source-file read stalled inside
the operating system can still delay feeder cleanup until the OS returns. The helper
does not delete original or rejected archives. Keep both bootstrap scripts paired
with their release and retain historical helpers with original profiles.

## Verification and support boundary

Regressions cover forged completed-state payloads, current and changed save bytes,
sheet-bound multi-event approval, literal identifiers, workbook temporary-file
substitution, managed route identifiers, bundle replacement and profile ancestry.
Real GPG tests use a public-key-only adversary, genuine restore/retry, interrupted
publication, compression expansion, input types, byte counts and process deadlines.
Tests use synthetic workbooks, isolated private stores and disposable keys.

Verified HTTPS and independently provisioned V7 signer trust remain required.
The Linux lifecycle is separate from operational V3's independently provisioned
witness requirement. Native Windows compatibility and development-key rehearsals
do not grant Windows CNG production qualification. No numerical model or production
eligibility is promoted by this maintenance release.
