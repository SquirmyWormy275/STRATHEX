# Security Cloud repairs — 2026-10-19

The eight STRATHEX findings against `bcfe4e50e1449b2585a037215c79f5a7e955e9da`
are addressed at their output, transport and workflow boundaries. Numeric models,
engine selection, source pins and handicap mathematics are unchanged.

## Workbook and display boundaries

Roster and result strings are saved as explicit XLSX text cells, including strings
beginning with `=`, `+`, `-` or `@`. Ordinary text and competitor IDs retain their
values. Existing workbooks are not rewritten by this repair. Bracket HTML escapes
every data value and includes a restrictive content security policy. The terminal
entry point filters CSI, OSC and other control strings, C0/C1 and Unicode direction
controls before stdout/stderr output. Carriage-return animation frames become lines.
These protections affect rendering and new writes, not stored competitor identities.

## Authenticated HTTP services

V2 HTTP now requires **HTTPS even on loopback**, with certificate verification.
The default direct Python V2 transport remains unchanged. A private installation CA
can be provisioned through `STRATHMARK_API_CA_BUNDLE`. The endpoint certificate
must match the configured host; certificate errors stop the selected operation.

V7 V3 also requires loopback HTTPS and a separately provisioned
`STRATHMARK_V3_SIGNER_IDENTITY_DIGEST`. Provision that digest from the installation's
trusted signer configuration, never from an initial network readiness response.
Use `STRATHMARK_V3_CA_BUNDLE` for the installation CA when needed. TLS authenticates
the service before bearer bytes are transmitted. Readiness and saved competition
signer trust must match the independent digest. Certificate verification, redirect
rejection, source/contract pins and credential references remain mandatory.

The frozen V7 contract signs pre-field receipts but does not provide a signature
on every lifecycle dictionary. Lifecycle responses are authenticated by the verified
TLS channel; they are not newly claimed to be independently signed artifacts.
Changing that persisted-artifact property requires a coordinated future contract.
V7 remains rehearsal-only; the separate Linux subprocess V3 profile is unchanged.

The installed V7 synthetic pair script provisions an ephemeral certificate and
signer digest through local fixture setup before starting the network listener.
It does not learn trust from an unauthenticated network response.

## Field changes and official evidence

New event IDs are opaque and independent of display order. Removing an unused,
unreferenced draft only changes display order. Assigned events, payments, schedules,
calculation history, receipts and official results prevent physical deletion.
Existing IDs are preserved; cancelled/finished events are not erased.

Changing a draft field, roster, wood or scratch/restoration archives its prior draft
marks and rounds, clears current calculations and approval, and clears the day
schedule. Restoring a competitor rebuilds the field DataFrame from the retained
roster so stable IDs and displayed membership agree. Issued/receipted fields,
started rounds and official results block destructive setup changes; use the
existing correction/recovery workflow. Roster replacement cannot erase existing
assignments or fee history.

Calculated V2 sheets bind ordered names and stable IDs, wood, event, stands, format,
cutoff and the saved authority revision. Single-event approval binds that context
and the entire mark sheet to judge identity and time. Generate heats, record
results, generate later rounds and export schedules require matching approval;
round marks must agree with the reviewed sheet. Newly calculated later-round marks
need their own review. Cancelling approval or editing a mark clears eligibility.
Failed recalculation cannot retain an earlier usable sheet or pending schedule.

Older unfinished saves without context/approval evidence must be recalculated and
reviewed before official use. Existing completed result histories are preserved.
A local operator able to rewrite code and authority files remains trusted; these
checks enforce normal workflow integrity, not a hostile machine administrator.

## Validation

Regression coverage includes formula-leading and Unicode roster values, all bracket
HTML contexts, terminal controls, stable event references, unapproved/stale mark
sheets, issued/result preservation, and a real TLS listener proving that an
untrusted certificate cannot receive the V3 bearer. Release checks use synthetic
workbooks and isolated databases, with no production deployment or operator-data
migration.

The initial-heat regeneration command also rejects any started or completed round. It cannot overwrite existing official results after a prior approval.
