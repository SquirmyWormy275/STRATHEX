"""Durable competition-scoped prediction-engine authority.

SQLite is the canonical authority for a scope's engine selection and lock. JSON
tournament saves contain only :class:`AuthorityReference`, so actor details,
reasons, and mutable lifecycle state cannot fork across copied or stale saves.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, MutableMapping
from uuid import uuid4

_ENGINES = frozenset({"v2", "v3"})
_MODES = frozenset({"production", "rehearsal"})
_OWNER_KINDS = frozenset({"single_event", "tournament"})
_IDENTITY_KINDS = frozenset({"tournament", "round", "field", "stand", "competitor", "command"})
_REFERENCE_KEYS = frozenset({"authority_store_id", "scope_id", "revision", "digest", "save_id"})


class AuthorityStateError(ValueError):
    """Raised when persisted selection authority is stale, mixed, or invalid."""


class LegacyMigrationRequired(AuthorityStateError):
    """Raised when a legacy state cannot perform numeric work yet."""

    def __init__(self, status: str) -> None:
        self.status = status
        super().__init__(f"legacy prediction authority requires {status}")


def _required_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AuthorityStateError(f"{label} must be a non-empty string")
    return value.strip()


def _canonical_json(value: Mapping[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _digest(value: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class AuthorityReference:
    authority_store_id: str
    scope_id: str
    revision: int
    digest: str
    save_id: str

    @classmethod
    def from_json(cls, value: Mapping[str, Any]) -> AuthorityReference:
        if not isinstance(value, Mapping) or set(value) != _REFERENCE_KEYS:
            raise AuthorityStateError("prediction_authority_ref has an invalid shape")
        revision = value.get("revision")
        digest = value.get("digest")
        if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
            raise AuthorityStateError("prediction_authority_ref revision must be a positive integer")
        if not isinstance(digest, str) or len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
            raise AuthorityStateError("prediction_authority_ref digest must be lowercase SHA-256")
        return cls(
            authority_store_id=_required_text(value.get("authority_store_id"), "authority_store_id"),
            scope_id=_required_text(value.get("scope_id"), "scope_id"),
            revision=revision,
            digest=digest,
            save_id=_required_text(value.get("save_id"), "save_id"),
        )

    def to_json(self) -> dict[str, Any]:
        return {
            "authority_store_id": self.authority_store_id,
            "scope_id": self.scope_id,
            "revision": self.revision,
            "digest": self.digest,
            "save_id": self.save_id,
        }


@dataclass(frozen=True)
class SelectionReceipt:
    reference: AuthorityReference
    owner_kind: str
    engine: str | None
    actor: str | None
    selected_at: str | None
    reason_code: str | None
    reason_note: str | None
    mode: str | None
    contract_identity: str | None
    source_identity: str | None
    pre_field_signer_trust: dict[str, str] | None
    locked: bool
    lock_boundary: str | None
    locked_at: str | None
    status: str
    migration_status: str
    abandoned_by: str | None
    abandonment_reason: str | None
    abandoned_at: str | None


def derive_scope_identity(scope_id: str, kind: str, local_id: str, *, revision: int = 1) -> str:
    """Derive a stable pseudonymous child identity from root-local facts."""
    scope_id = _required_text(scope_id, "scope_id")
    kind = _required_text(kind, "identity kind")
    local_id = _required_text(local_id, "local_id")
    if kind not in _IDENTITY_KINDS:
        raise AuthorityStateError(f"unsupported identity kind: {kind}")
    if not isinstance(revision, int) or isinstance(revision, bool) or revision < 1:
        raise AuthorityStateError("identity revision must be a positive integer")
    material = f"{scope_id}\0{kind}\0{local_id}\0{revision}".encode()
    return f"{kind}:{hashlib.sha256(material).hexdigest()}"


class PredictionAuthorityStore:
    """Canonical SQLite store for engine selection, locking, and save binding."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS authority_meta (
                    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
                    store_id TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS prediction_scopes (
                    scope_id TEXT PRIMARY KEY,
                    save_id TEXT NOT NULL UNIQUE,
                    revision INTEGER NOT NULL,
                    payload_json TEXT NOT NULL,
                    digest TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS prediction_scope_history (
                    scope_id TEXT NOT NULL,
                    revision INTEGER NOT NULL,
                    payload_json TEXT NOT NULL,
                    digest TEXT NOT NULL,
                    PRIMARY KEY (scope_id, revision)
                );
                CREATE TABLE IF NOT EXISTS authority_save_bindings (
                    save_id TEXT PRIMARY KEY,
                    scope_id TEXT NOT NULL,
                    normalized_path TEXT NOT NULL,
                    FOREIGN KEY (scope_id) REFERENCES prediction_scopes(scope_id)
                );
                """
            )
            row = connection.execute("SELECT store_id FROM authority_meta WHERE singleton = 1").fetchone()
            if row is None:
                connection.execute(
                    "INSERT INTO authority_meta(singleton, store_id) VALUES (1, ?)",
                    (f"strathex-authority:{uuid4()}",),
                )

    @property
    def store_id(self) -> str:
        with self._connect() as connection:
            row = connection.execute("SELECT store_id FROM authority_meta WHERE singleton = 1").fetchone()
        assert row is not None
        return str(row["store_id"])

    def _reference(self, payload: Mapping[str, Any], *, save_id: str) -> AuthorityReference:
        return AuthorityReference(
            authority_store_id=self.store_id,
            scope_id=str(payload["scope_id"]),
            revision=int(payload["revision"]),
            digest=_digest(payload),
            save_id=save_id,
        )

    @staticmethod
    def _receipt(payload: Mapping[str, Any], reference: AuthorityReference) -> SelectionReceipt:
        return SelectionReceipt(
            reference=reference,
            owner_kind=str(payload["owner_kind"]),
            engine=payload.get("engine"),
            actor=payload.get("actor"),
            selected_at=payload.get("selected_at"),
            reason_code=payload.get("reason_code"),
            reason_note=payload.get("reason_note"),
            mode=payload.get("mode"),
            contract_identity=payload.get("contract_identity"),
            source_identity=payload.get("source_identity"),
            pre_field_signer_trust=(
                dict(payload["pre_field_signer_trust"])
                if isinstance(payload.get("pre_field_signer_trust"), Mapping)
                else None
            ),
            locked=bool(payload["locked"]),
            lock_boundary=payload.get("lock_boundary"),
            locked_at=payload.get("locked_at"),
            status=str(payload["status"]),
            migration_status=str(payload["migration_status"]),
            abandoned_by=payload.get("abandoned_by"),
            abandonment_reason=payload.get("abandonment_reason"),
            abandoned_at=payload.get("abandoned_at"),
        )

    def _write(self, connection: sqlite3.Connection, payload: Mapping[str, Any], *, save_id: str) -> SelectionReceipt:
        payload_json = _canonical_json(payload)
        digest = _digest(payload)
        connection.execute(
            """INSERT INTO prediction_scopes(scope_id, save_id, revision, payload_json, digest)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(scope_id) DO UPDATE SET
                 save_id=excluded.save_id, revision=excluded.revision,
                 payload_json=excluded.payload_json, digest=excluded.digest""",
            (payload["scope_id"], save_id, payload["revision"], payload_json, digest),
        )
        connection.execute(
            """INSERT INTO prediction_scope_history(scope_id, revision, payload_json, digest)
               VALUES (?, ?, ?, ?)""",
            (payload["scope_id"], payload["revision"], payload_json, digest),
        )
        reference = self._reference(payload, save_id=save_id)
        return self._receipt(payload, reference)

    def create_scope(self, *, owner_kind: str, scope_id: str | None = None) -> SelectionReceipt:
        if owner_kind not in _OWNER_KINDS:
            raise AuthorityStateError(f"unsupported owner_kind: {owner_kind}")
        scope_id = scope_id or f"tournament:{uuid4()}"
        scope_id = _required_text(scope_id, "scope_id")
        payload = {
            "scope_id": scope_id,
            "owner_kind": owner_kind,
            "revision": 1,
            "engine": None,
            "actor": None,
            "selected_at": None,
            "reason_code": None,
            "reason_note": None,
            "mode": None,
            "contract_identity": None,
            "source_identity": None,
            "pre_field_signer_trust": None,
            "locked": False,
            "lock_boundary": None,
            "locked_at": None,
            "status": "open",
            "migration_status": "selection_required",
            "abandoned_by": None,
            "abandonment_reason": None,
            "abandoned_at": None,
        }
        try:
            with self._connect() as connection:
                return self._write(connection, payload, save_id=f"strathex-save:{uuid4()}")
        except sqlite3.IntegrityError as exc:
            raise AuthorityStateError(f"scope already exists: {scope_id}") from exc

    def resolve(self, reference: AuthorityReference | Mapping[str, Any]) -> SelectionReceipt:
        if not isinstance(reference, AuthorityReference):
            reference = AuthorityReference.from_json(reference)
        if reference.authority_store_id != self.store_id:
            raise AuthorityStateError("authority store identity mismatch")
        with self._connect() as connection:
            row = connection.execute(
                "SELECT save_id, revision, payload_json, digest FROM prediction_scopes WHERE scope_id = ?",
                (reference.scope_id,),
            ).fetchone()
        if row is None:
            raise AuthorityStateError("prediction authority scope is missing")
        if row["save_id"] != reference.save_id:
            raise AuthorityStateError("prediction authority save identity mismatch")
        if int(row["revision"]) != reference.revision or row["digest"] != reference.digest:
            raise AuthorityStateError("prediction authority reference is stale or ahead")
        payload = json.loads(row["payload_json"])
        if _digest(payload) != reference.digest:
            raise AuthorityStateError("prediction authority canonical digest mismatch")
        return self._receipt(payload, reference)

    def _mutate(self, reference: AuthorityReference, changes: Mapping[str, Any]) -> SelectionReceipt:
        current = self.resolve(reference)
        payload = {
            "scope_id": current.reference.scope_id,
            "owner_kind": current.owner_kind,
            "revision": current.reference.revision + 1,
            "engine": current.engine,
            "actor": current.actor,
            "selected_at": current.selected_at,
            "reason_code": current.reason_code,
            "reason_note": current.reason_note,
            "mode": current.mode,
            "contract_identity": current.contract_identity,
            "source_identity": current.source_identity,
            "pre_field_signer_trust": current.pre_field_signer_trust,
            "locked": current.locked,
            "lock_boundary": current.lock_boundary,
            "locked_at": current.locked_at,
            "status": current.status,
            "migration_status": current.migration_status,
            "abandoned_by": current.abandoned_by,
            "abandonment_reason": current.abandonment_reason,
            "abandoned_at": current.abandoned_at,
        }
        payload.update(changes)
        with self._connect() as connection:
            return self._write(connection, payload, save_id=current.reference.save_id)

    def select_engine(
        self,
        reference: AuthorityReference,
        *,
        engine: str,
        actor: str,
        selected_at: str,
        reason_code: str,
        mode: str,
        contract_identity: str,
        source_identity: str,
        pre_field_signer_trust: Mapping[str, str] | None = None,
        reason_note: str | None = None,
    ) -> SelectionReceipt:
        current = self.resolve(reference)
        if current.status != "open":
            raise AuthorityStateError("closed or abandoned scope cannot select an engine")
        if current.locked:
            raise AuthorityStateError("prediction engine selection is locked")
        if engine not in _ENGINES:
            raise AuthorityStateError(f"unsupported prediction engine: {engine}")
        if mode not in _MODES:
            raise AuthorityStateError(f"unsupported prediction mode: {mode}")
        reason_code = _required_text(reason_code, "selection reason")
        if current.engine is not None and current.engine != engine and not reason_code:
            raise AuthorityStateError("engine change requires a reason")
        if engine == "v2" and mode != "production":
            raise AuthorityStateError("V2 selection must use production mode")
        if engine == "v3" and mode != "rehearsal":
            raise AuthorityStateError("V3 selection is rehearsal-only until an explicit cutover release")
        return self._mutate(
            reference,
            {
                "engine": engine,
                "actor": _required_text(actor, "actor"),
                "selected_at": _required_text(selected_at, "selected_at"),
                "reason_code": reason_code,
                "reason_note": reason_note.strip() if isinstance(reason_note, str) and reason_note.strip() else None,
                "mode": mode,
                "contract_identity": _required_text(contract_identity, "contract_identity"),
                "source_identity": _required_text(source_identity, "source_identity"),
                "pre_field_signer_trust": (None if pre_field_signer_trust is None else dict(pre_field_signer_trust)),
                "migration_status": "ready",
            },
        )

    def lock(self, reference: AuthorityReference, *, boundary: str, locked_at: str) -> SelectionReceipt:
        current = self.resolve(reference)
        if current.engine is None:
            raise AuthorityStateError("cannot lock a scope before selecting an engine")
        if current.locked:
            if current.lock_boundary == boundary and current.locked_at == locked_at:
                return current
            raise AuthorityStateError("prediction engine selection is already locked")
        return self._mutate(
            reference,
            {
                "locked": True,
                "lock_boundary": _required_text(boundary, "lock boundary"),
                "locked_at": _required_text(locked_at, "locked_at"),
            },
        )

    def abandon(self, reference: AuthorityReference, *, actor: str, reason: str, abandoned_at: str) -> SelectionReceipt:
        current = self.resolve(reference)
        if not current.locked:
            raise AuthorityStateError("only a locked scope can be terminally abandoned")
        return self._mutate(
            reference,
            {
                "status": "abandoned",
                "migration_status": "terminal",
                "abandoned_by": _required_text(actor, "actor"),
                "abandonment_reason": _required_text(reason, "abandonment reason"),
                "abandoned_at": _required_text(abandoned_at, "abandoned_at"),
            },
        )

    def bind_save_path(self, reference: AuthorityReference, path: str | Path) -> None:
        self.resolve(reference)
        normalized = str(Path(path).resolve()).casefold()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT normalized_path FROM authority_save_bindings WHERE save_id = ?", (reference.save_id,)
            ).fetchone()
            if row is not None and row["normalized_path"] != normalized:
                raise AuthorityStateError("authority reference belongs to a different save path")
            connection.execute(
                "INSERT OR IGNORE INTO authority_save_bindings(save_id, scope_id, normalized_path) VALUES (?, ?, ?)",
                (reference.save_id, reference.scope_id, normalized),
            )

    def validate_save_path(self, reference: AuthorityReference, path: str | Path) -> SelectionReceipt:
        receipt = self.resolve(reference)
        normalized = str(Path(path).resolve()).casefold()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT normalized_path FROM authority_save_bindings WHERE save_id = ?", (reference.save_id,)
            ).fetchone()
        if row is None or row["normalized_path"] != normalized:
            raise AuthorityStateError("authority reference is not reconciled to this save path")
        return receipt


def attach_authority_reference(
    state: MutableMapping[str, Any], reference: AuthorityReference | Mapping[str, Any]
) -> None:
    """Attach only the immutable canonical reference to root JSON state."""
    if not isinstance(reference, AuthorityReference):
        reference = AuthorityReference.from_json(reference)
    state["prediction_authority_ref"] = reference.to_json()
    state.pop("prediction_authority_runtime", None)


def _has_numeric_evidence(value: Any) -> tuple[bool, set[str]]:
    found = False
    engines: set[str] = set()
    if isinstance(value, Mapping):
        for key, item in value.items():
            if key in {"handicap_results", "handicap_results_all", "predictions"} and item:
                found = True
            if key == "engine_version" and item is not None:
                engines.add("v2" if str(item).startswith("2.") else str(item))
            child_found, child_engines = _has_numeric_evidence(item)
            found = found or child_found
            engines.update(child_engines)
    elif isinstance(value, list):
        for item in value:
            child_found, child_engines = _has_numeric_evidence(item)
            found = found or child_found
            engines.update(child_engines)
    return found, engines


def classify_legacy_state(state: Mapping[str, Any]) -> str:
    """Name the deliberate migration required before legacy numeric work."""
    found, engines = _has_numeric_evidence(state)
    if not found:
        return "selection_required"
    if engines == {"v2"}:
        return "legacy_v2_confirmation_required"
    return "reconciliation_required"


def resolve_authority_for_state(
    root_state: Mapping[str, Any],
    store: PredictionAuthorityStore,
    *,
    child: Mapping[str, Any] | None = None,
) -> SelectionReceipt:
    """Resolve one root authority; a child can inherit but never override it."""
    if child is not None and "prediction_authority_ref" in child:
        raise AuthorityStateError("child event cannot override tournament prediction authority")
    reference_payload = root_state.get("prediction_authority_ref")
    if reference_payload is None:
        raise LegacyMigrationRequired(classify_legacy_state(root_state))
    receipt = store.resolve(AuthorityReference.from_json(reference_payload))
    if receipt.engine is None or receipt.migration_status != "ready":
        raise LegacyMigrationRequired(receipt.migration_status)
    if receipt.status != "open":
        raise AuthorityStateError(f"prediction authority scope is {receipt.status}")
    return receipt


def confirm_legacy_v2(
    state: MutableMapping[str, Any],
    store: PredictionAuthorityStore,
    *,
    actor: str,
    confirmed_at: str,
    contract_identity: str,
    source_identity: str,
) -> SelectionReceipt:
    """Explicitly bind proven legacy V2 evidence without rewriting that evidence."""
    migration = classify_legacy_state(state)
    if migration != "legacy_v2_confirmation_required":
        raise LegacyMigrationRequired(migration)
    owner_kind = "tournament" if isinstance(state.get("events"), list) else "single_event"
    created = store.create_scope(owner_kind=owner_kind)
    selected = store.select_engine(
        created.reference,
        engine="v2",
        actor=actor,
        selected_at=confirmed_at,
        reason_code="legacy_v2_confirmed",
        mode="production",
        contract_identity=contract_identity,
        source_identity=source_identity,
    )
    attach_authority_reference(state, selected.reference)
    return selected


def runtime_authority_status(
    state: Mapping[str, Any],
    store: PredictionAuthorityStore | None,
    *,
    save_path: str | Path | None = None,
) -> dict[str, Any]:
    """Return non-serialized, judge-facing readiness for a loaded state."""
    reference_payload = state.get("prediction_authority_ref")
    if reference_payload is None:
        return {"status": classify_legacy_state(state), "numeric_work_allowed": False}
    reference = AuthorityReference.from_json(reference_payload)
    if store is None:
        return {"status": "authority_store_required", "numeric_work_allowed": False}
    receipt = store.validate_save_path(reference, save_path) if save_path is not None else store.resolve(reference)
    return {
        "status": "ready" if receipt.engine is not None and receipt.status == "open" else receipt.migration_status,
        "numeric_work_allowed": receipt.engine is not None and receipt.status == "open",
        "scope_id": receipt.reference.scope_id,
        "engine": receipt.engine,
        "mode": receipt.mode,
        "locked": receipt.locked,
        "contract_identity": receipt.contract_identity,
        "source_identity": receipt.source_identity,
    }
