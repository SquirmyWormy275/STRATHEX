"""Competition-scoped prediction-engine routing.

The durable authority store owns the judge's selection.  This module turns one
locked authority receipt into an immutable execution context and routes a
numeric field operation to exactly that engine.  Transport policy remains
inside each engine adapter; an adapter error is never interpreted as permission
to call the other engine.

The V3 transport is deliberately not implemented here.  Until its public
consumer contract is frozen and wired, a V3-selected call fails closed with a
typed :class:`EngineAdapterUnavailableError`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Protocol, TypeAlias

from woodchopping.ui.prediction_context import SelectionReceipt

EngineProjection: TypeAlias = list[dict[str, Any]]


class ExecutionContextError(ValueError):
    """Raised when numeric work is not bound to valid locked authority."""


class EngineAdapterUnavailableError(RuntimeError):
    """Raised when the selected engine has no configured adapter."""


class EngineResultMismatchError(RuntimeError):
    """Raised when an adapter returns evidence from a different engine."""


class V2FieldAdapter(Protocol):
    """Existing V2 call shape, intentionally unchanged by selection routing."""

    def __call__(self, **request: Any) -> EngineProjection: ...


class V3FieldAdapter(Protocol):
    """Future V3 boundary, which must receive the immutable scope context."""

    def __call__(
        self,
        *,
        execution_context: PredictionExecutionContext,
        **request: Any,
    ) -> EngineProjection: ...


def _required_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ExecutionContextError(f"{label} must be a non-empty string")
    return value.strip()


@dataclass(frozen=True, slots=True)
class PredictionExecutionContext:
    """Immutable selection and lock facts required by one numeric operation."""

    authority_store_id: str
    scope_id: str
    authority_revision: int
    authority_digest: str
    selected_engine: str
    mode: str
    contract_identity: str
    source_identity: str
    selected_by_actor_id: str
    selected_at_utc: str
    reason_code: str
    locked: bool
    lock_boundary: str
    locked_at: str
    pre_field_signer_trust_json: str | None = None

    def __post_init__(self) -> None:
        for field_name in (
            "authority_store_id",
            "scope_id",
            "authority_digest",
            "selected_engine",
            "mode",
            "contract_identity",
            "source_identity",
            "selected_by_actor_id",
            "selected_at_utc",
            "reason_code",
            "lock_boundary",
            "locked_at",
        ):
            object.__setattr__(self, field_name, _required_text(getattr(self, field_name), field_name))
        if (
            not isinstance(self.authority_revision, int)
            or isinstance(self.authority_revision, bool)
            or self.authority_revision < 1
        ):
            raise ExecutionContextError("authority_revision must be a positive integer")
        if len(self.authority_digest) != 64 or any(char not in "0123456789abcdef" for char in self.authority_digest):
            raise ExecutionContextError("authority_digest must be lowercase SHA-256")
        if self.selected_engine not in {"v2", "v3"}:
            raise ExecutionContextError(f"unsupported selected engine: {self.selected_engine}")
        if self.mode not in {"production", "rehearsal"}:
            raise ExecutionContextError(f"unsupported prediction mode: {self.mode}")
        if self.selected_engine == "v2" and self.mode != "production":
            raise ExecutionContextError("V2 execution context must use production mode")
        if self.locked is not True:
            raise ExecutionContextError("prediction engine selection must be locked before numeric work")

    @classmethod
    def from_receipt(cls, receipt: SelectionReceipt) -> PredictionExecutionContext:
        """Snapshot one canonical receipt without retaining mutable store access."""
        if not isinstance(receipt, SelectionReceipt):
            raise ExecutionContextError("selection receipt is required")
        if receipt.engine is None:
            raise ExecutionContextError("selection receipt has no selected engine")
        if receipt.status != "open":
            raise ExecutionContextError(f"prediction authority scope is {receipt.status}")
        if receipt.migration_status != "ready":
            raise ExecutionContextError(f"prediction authority requires {receipt.migration_status} before numeric work")
        if not receipt.locked:
            raise ExecutionContextError("prediction engine selection must be locked before numeric work")
        return cls(
            authority_store_id=receipt.reference.authority_store_id,
            scope_id=receipt.reference.scope_id,
            authority_revision=receipt.reference.revision,
            authority_digest=receipt.reference.digest,
            selected_engine=receipt.engine,
            mode=receipt.mode or "",
            contract_identity=receipt.contract_identity or "",
            source_identity=receipt.source_identity or "",
            selected_by_actor_id=receipt.actor or "",
            selected_at_utc=receipt.selected_at or "",
            reason_code=receipt.reason_code or "",
            locked=receipt.locked,
            lock_boundary=receipt.lock_boundary or "",
            locked_at=receipt.locked_at or "",
            pre_field_signer_trust_json=(
                None
                if receipt.pre_field_signer_trust is None
                else json.dumps(
                    receipt.pre_field_signer_trust,
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=False,
                )
            ),
        )


def _verify_returned_engine(
    projection: EngineProjection,
    *,
    selected_engine: str,
) -> None:
    """Reject a whole field if any returned row names the wrong engine."""
    if not isinstance(projection, list):
        raise EngineResultMismatchError("selected engine adapter returned an invalid field projection")
    expected_major = "2." if selected_engine == "v2" else "3."
    for row in projection:
        if not isinstance(row, Mapping):
            raise EngineResultMismatchError("selected engine adapter returned an invalid result row")
        returned_version = row.get("engine_version")
        if not isinstance(returned_version, str) or not returned_version.startswith(expected_major):
            raise EngineResultMismatchError(
                "selected engine does not match returned engine evidence "
                f"({selected_engine!r} selected, {returned_version!r} returned)"
            )


class EngineRouter:
    """Route one field to exactly the engine named by locked authority."""

    def __init__(
        self,
        *,
        v2_adapter: V2FieldAdapter,
        v3_adapter: V3FieldAdapter | None = None,
    ) -> None:
        if not callable(v2_adapter):
            raise TypeError("v2_adapter must be callable")
        if v3_adapter is not None and not callable(v3_adapter):
            raise TypeError("v3_adapter must be callable")
        self._v2_adapter: Callable[..., EngineProjection] = v2_adapter
        self._v3_adapter: Callable[..., EngineProjection] | None = v3_adapter

    @property
    def v3_adapter(self) -> V3FieldAdapter | None:
        """Expose the selected adapter only for explicit recovery orchestration."""
        return self._v3_adapter

    def calculate_field(
        self,
        execution_context: PredictionExecutionContext,
        **request: Any,
    ) -> EngineProjection:
        """Calculate without fallback and return the adapter projection verbatim."""
        if not isinstance(execution_context, PredictionExecutionContext):
            raise ExecutionContextError("immutable prediction execution context is required")

        if execution_context.selected_engine == "v2":
            projection = self._v2_adapter(**request)
        elif execution_context.selected_engine == "v3":
            if self._v3_adapter is None:
                raise EngineAdapterUnavailableError(
                    "V3 adapter is not wired; the selected engine cannot calculate this field"
                )
            projection = self._v3_adapter(execution_context=execution_context, **request)
        else:  # Defensive guard for contexts reconstructed by unsafe external code.
            raise ExecutionContextError(f"unsupported selected engine: {execution_context.selected_engine}")

        _verify_returned_engine(
            projection,
            selected_engine=execution_context.selected_engine,
        )
        return projection
