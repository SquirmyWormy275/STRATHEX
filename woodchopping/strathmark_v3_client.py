"""Fail-closed authenticated loopback client for the frozen STRATHMARK V3 API."""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Protocol
from urllib.parse import urlencode, urlparse

import requests
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

from woodchopping.engine_selection import EngineProjection, PredictionExecutionContext
from woodchopping.v3_authority_store import V3CommandStore

FROZEN_V3_CONTRACT_DIGEST = "20174ab13d32c74419e90bfdc73e6b5d5e3e888e1a6cf098f20e585c3bf2ec24"
FROZEN_V3_CONTRACT_VERSION = "strathmark.v3-consumer-contract.v7"
FROZEN_V3_SOURCE_COMMIT = "1ede920505e90a3015ad3338a140ef96029e0b72"
_ENVIRONMENT_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_FIELD_RECEIPT_CONTENT_KEYS = (
    "schema_version",
    "field_id",
    "upstream_field_revision",
    "receipt_revision",
    "supersedes_receipt_id",
    "ordered_competitor_ids",
    "target_context",
    "target_context_digest",
    "historical_cutoff_key",
    "tournament_epoch_id",
    "tournament_event_sequence",
    "packet_identities",
    "sections",
    "marks",
    "warning_codes",
    "total_latency_ms",
    "bundles",
    "engine_authority",
)
_PRE_FIELD_RECEIPT_CONTENT_KEYS = (
    "schema_version",
    "purpose",
    "issued_mark",
    "snapshot",
    "forecasts",
    "created_at",
)


class V3ClientError(RuntimeError):
    """The selected V3 boundary could not produce trusted evidence."""


class V3RecoveryRequired(V3ClientError):
    """A command may have reached STRATHMARK and must be reconciled."""

    def __init__(self, command_key: str) -> None:
        self.command_key = command_key
        super().__init__(f"V3 command requires recovery: {command_key}")


class V3RuntimeConfigurationError(V3ClientError):
    """The local V3 installation is absent or does not match reviewed pins."""


class CredentialProvider(Protocol):
    def __call__(self) -> str: ...


class HttpTransport(Protocol):
    def request(self, method: str, url: str, **kwargs: Any) -> Any: ...


class UtcClock(Protocol):
    def __call__(self) -> datetime: ...


@dataclass(frozen=True, slots=True)
class V3Readiness:
    state: str
    service: str
    release_posture: str
    production_authority: str
    contract_digest: str
    source_commit: str
    detail: str | None = None
    pre_field_signer_trust_json: str | None = None


def _canonical_json(value: Mapping[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _digest_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _loopback_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme != "http" or parsed.hostname not in {
        "127.0.0.1",
        "localhost",
        "::1",
    }:
        raise ValueError("STRATHMARK V3 client requires an explicit loopback HTTP URL")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("STRATHMARK V3 base URL cannot contain credentials, query, or fragment")
    if parsed.path not in {"", "/"}:
        raise ValueError("STRATHMARK V3 base URL must be a loopback origin without a path")
    return value.rstrip("/")


def _receipt_content_digest(receipt: Mapping[str, Any], keys: tuple[str, ...]) -> str:
    content = {key: receipt[key] for key in keys}
    return _digest_text(_canonical_json(content))


def _validated_pre_field_signer_trust(
    value: Any,
    *,
    source_commit: str,
) -> tuple[str, ec.EllipticCurvePublicKey]:
    expected = {
        "schema_version",
        "algorithm",
        "key_id",
        "key_class",
        "provider",
        "public_key_der_b64",
        "identity_digest",
        "service_binding_digest",
    }
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError
    trust = {str(key): str(item) for key, item in value.items()}
    identity = {key: trust[key] for key in ("key_id", "key_class", "provider", "public_key_der_b64")}
    binding = {
        "schema_version": "strathmark-v3-pre-field-signer-service-binding-v1",
        "source_commit": source_commit,
        "consumer_contract_version": FROZEN_V3_CONTRACT_VERSION,
        "consumer_contract_digest": FROZEN_V3_CONTRACT_DIGEST,
        "pre_field_signer_identity_digest": trust["identity_digest"],
    }
    if (
        trust["schema_version"] != "strathmark-v3-pre-field-signer-trust-v1"
        or trust["algorithm"] != "ecdsa-p256-sha256"
        or re.fullmatch(r"[a-z][a-z0-9_.:-]{0,127}", trust["key_id"]) is None
        or trust["key_class"] not in {"development_ephemeral", "production_cng"}
        or re.fullmatch(r"[a-z][a-z0-9_.:-]{0,127}", trust["provider"]) is None
        or trust["identity_digest"] != _digest_text(_canonical_json(identity))
        or trust["service_binding_digest"] != _digest_text(_canonical_json(binding))
    ):
        raise ValueError
    try:
        public_der = base64.b64decode(trust["public_key_der_b64"], validate=True)
        public_key = serialization.load_der_public_key(public_der)
    except (TypeError, ValueError, binascii.Error) as exc:
        raise ValueError from exc
    if not isinstance(public_key, ec.EllipticCurvePublicKey) or not isinstance(public_key.curve, ec.SECP256R1):
        raise ValueError
    return _canonical_json(trust), public_key


def _validate_structural_manifest(
    manifest: Mapping[str, Any],
    *,
    expected_kind: str,
    expected_payload: Mapping[str, Any],
    trusted_signer_trust_json: str,
) -> None:
    """Validate canonical receipt integrity and its competition-pinned signature."""
    expected_fields = {
        "schema_version",
        "kind",
        "body_json",
        "body_digest",
        "key_id",
        "signature_der_b64",
    }
    if not isinstance(manifest, Mapping) or set(manifest) != expected_fields:
        raise ValueError
    body_json = manifest["body_json"]
    if not isinstance(body_json, str):
        raise ValueError
    body = json.loads(body_json)
    try:
        signature = base64.b64decode(manifest["signature_der_b64"], validate=True)
    except (TypeError, ValueError, binascii.Error) as exc:
        raise ValueError from exc
    if (
        not isinstance(body, dict)
        or body_json != _canonical_json(body)
        or manifest["schema_version"] != "strathmark-v3-signed-manifest-v1"
        or manifest["kind"] != expected_kind
        or body.get("schema_version") != "strathmark-v3-integrity-body-v1"
        or body.get("kind") != expected_kind
        or body.get("algorithm") != "ecdsa-p256-sha256"
        or body.get("key_id") != manifest["key_id"]
        or body.get("created_at") != expected_payload.get("created_at")
        or body.get("payload") != expected_payload
        or manifest["body_digest"] != _digest_text(body_json)
        or not signature
    ):
        raise ValueError
    trust, public_key = _validated_pre_field_signer_trust(
        json.loads(trusted_signer_trust_json),
        source_commit=FROZEN_V3_SOURCE_COMMIT,
    )
    trusted = json.loads(trust)
    if manifest["key_id"] != trusted["key_id"]:
        raise ValueError
    try:
        public_key.verify(signature, body_json.encode("utf-8"), ec.ECDSA(hashes.SHA256()))
    except InvalidSignature as exc:
        raise ValueError from exc


class V3HttpClient:
    """Frozen-contract client with durable exact-retry command authority."""

    _POST_SCHEMAS = {
        "open_scope": ("/v3/scopes/open", "strathmark-v3-scope-open-response-v1"),
        "synchronize_snapshot": (
            "/v3/snapshots/synchronize",
            "strathmark-v3-snapshot-sync-response-v1",
        ),
        "freeze_round": ("/v3/rounds/freeze", "strathmark-v3-round-freeze-response-v1"),
        "close_round": ("/v3/rounds/close", "strathmark-v3-round-close-response-v1"),
        "close_scope": ("/v3/scopes/close", "strathmark-v3-scope-close-response-v1"),
        "prepare_card": (
            "/v3/cards/prepare",
            "strathmark-v3-card-preparation-response-v1",
        ),
        "pre_field_forecast": (
            "/v3/forecasts/pre-field",
            "strathmark-v3-pre-field-forecast-response-v1",
        ),
        "assemble_field": (
            "/v3/fields/assemble",
            "strathmark-v3-field-assembly-response-v1",
        ),
        "lookup_receipt": (
            "/v3/receipts/lookup",
            "strathmark-v3-receipt-lookup-response-v1",
        ),
        "decide_approval": (
            "/v3/approvals/decide",
            "strathmark-v3-approval-decision-response-v1",
        ),
        "acknowledge_issue": (
            "/v3/issues/acknowledge",
            "strathmark-v3-issue-acknowledgment-response-v1",
        ),
        "settle_result": ("/v3/results/settle", "strathmark-v3-settlement-response-v1"),
    }

    def __init__(
        self,
        *,
        base_url: str,
        credential_provider: CredentialProvider,
        command_store: V3CommandStore,
        transport: HttpTransport | None = None,
        connect_timeout_seconds: float = 1.0,
        bundle_id: str = "bundle:strathex-current",
        clock: UtcClock | None = None,
    ) -> None:
        self.base_url = _loopback_url(base_url)
        if not callable(credential_provider):
            raise TypeError("credential_provider must be callable")
        if not isinstance(command_store, V3CommandStore):
            raise TypeError("command_store must be a V3CommandStore")
        self._credential_provider = credential_provider
        self.command_store = command_store
        if transport is None:
            session = requests.Session()
            session.trust_env = False
            self._transport = session
        else:
            self._transport = transport
        self._connect_timeout = float(connect_timeout_seconds)
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        if not isinstance(bundle_id, str) or not bundle_id.startswith("bundle:"):
            raise ValueError("V3 runtime bundle_id must be a namespaced bundle identifier")
        self.bundle_id = bundle_id

    def _remaining_deadline_ms(self, hard_deadline_at: str, *, maximum_ms: int) -> int:
        try:
            deadline = datetime.fromisoformat(hard_deadline_at.replace("Z", "+00:00"))
            now = self._clock()
        except (AttributeError, TypeError, ValueError) as exc:
            raise V3ClientError("V3 hard deadline is invalid") from exc
        if deadline.tzinfo is None or not isinstance(now, datetime) or now.tzinfo is None:
            raise V3ClientError("V3 hard deadline and clock must be timezone-aware")
        remaining_ms = int((deadline - now).total_seconds() * 1000)
        if remaining_ms < 25:
            raise V3ClientError("V3 field hard deadline expired before completion")
        return min(maximum_ms, remaining_ms)

    @staticmethod
    def _validate_context(context: PredictionExecutionContext) -> None:
        if not isinstance(context, PredictionExecutionContext) or context.selected_engine != "v3":
            raise V3ClientError("V3 client requires a locked V3 execution context")
        if context.contract_identity != FROZEN_V3_CONTRACT_DIGEST:
            raise V3ClientError("V3 consumer contract pin does not match the frozen contract")
        if context.source_identity != FROZEN_V3_SOURCE_COMMIT:
            raise V3ClientError("V3 source pin does not match the frozen source commit")
        try:
            _validated_pre_field_signer_trust(
                json.loads(context.pre_field_signer_trust_json or "null"),
                source_commit=context.source_identity,
            )
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise V3ClientError("V3 pre-field signer trust is absent or invalid") from exc

    def _headers(self, *, idempotency_key: str | None = None, action: str | None = None) -> dict[str, str]:
        credential = self._credential_provider()
        if not isinstance(credential, str) or not credential:
            raise V3ClientError("V3 service credential is unavailable")
        headers = {
            "Authorization": f"Bearer {credential}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if idempotency_key is not None:
            headers["Idempotency-Key"] = idempotency_key
        if action is not None:
            headers["X-STRATHMARK-Upstream-Action"] = action
        return headers

    @staticmethod
    def _body(response: Any, expected_schema: str) -> dict[str, Any]:
        try:
            body = response.json()
        except Exception as exc:
            raise V3ClientError("STRATHMARK V3 returned non-JSON evidence") from exc
        if not isinstance(body, dict):
            raise V3ClientError("STRATHMARK V3 returned a non-object response")
        if response.status_code < 200 or response.status_code >= 300:
            code = body.get("code") if isinstance(body.get("code"), str) else "request_rejected"
            raise V3ClientError(f"STRATHMARK V3 rejected the request ({code})")
        if body.get("schema_version") != expected_schema:
            raise V3ClientError("STRATHMARK V3 response does not match the frozen schema")
        return body

    def _readiness(self, mode: str | None = None) -> V3Readiness:
        try:
            response = self._transport.request(
                "GET",
                f"{self.base_url}/v3/status",
                headers=self._headers(action="read_status"),
                timeout=(self._connect_timeout, 5.0),
                allow_redirects=False,
            )
            body = self._body(response, "strathmark-v3-status-response-v1")
        except (requests.RequestException, V3ClientError) as exc:
            return V3Readiness(
                "status_check_failed",
                "unknown",
                "unknown",
                "unknown",
                FROZEN_V3_CONTRACT_DIGEST,
                FROZEN_V3_SOURCE_COMMIT,
                type(exc).__name__,
            )
        service = str(body.get("service"))
        posture = str(body.get("v3_readiness"))
        authority = str(body.get("production_authority"))
        returned_contract = body.get("consumer_contract_digest")
        returned_contract_version = body.get("consumer_contract_version")
        returned_source = body.get("source_commit")
        if returned_contract is None:
            return V3Readiness(
                "ineligible",
                service,
                posture,
                authority,
                FROZEN_V3_CONTRACT_DIGEST,
                FROZEN_V3_SOURCE_COMMIT,
                "consumer_contract_evidence_missing",
            )
        if returned_contract != FROZEN_V3_CONTRACT_DIGEST:
            return V3Readiness(
                "ineligible",
                service,
                posture,
                authority,
                FROZEN_V3_CONTRACT_DIGEST,
                FROZEN_V3_SOURCE_COMMIT,
                "consumer_contract_pin_mismatch",
            )
        if returned_contract_version is None:
            return V3Readiness(
                "ineligible",
                service,
                posture,
                authority,
                FROZEN_V3_CONTRACT_DIGEST,
                FROZEN_V3_SOURCE_COMMIT,
                "consumer_contract_version_missing",
            )
        if returned_contract_version != FROZEN_V3_CONTRACT_VERSION:
            return V3Readiness(
                "ineligible",
                service,
                posture,
                authority,
                FROZEN_V3_CONTRACT_DIGEST,
                FROZEN_V3_SOURCE_COMMIT,
                "consumer_contract_version_mismatch",
            )
        if returned_source is None:
            return V3Readiness(
                "ineligible",
                service,
                posture,
                authority,
                FROZEN_V3_CONTRACT_DIGEST,
                FROZEN_V3_SOURCE_COMMIT,
                "source_evidence_missing",
            )
        if returned_source != FROZEN_V3_SOURCE_COMMIT:
            return V3Readiness(
                "ineligible",
                service,
                posture,
                authority,
                FROZEN_V3_CONTRACT_DIGEST,
                FROZEN_V3_SOURCE_COMMIT,
                "source_pin_mismatch",
            )
        try:
            signer_trust_json, _public_key = _validated_pre_field_signer_trust(
                body.get("pre_field_signer_trust"),
                source_commit=returned_source,
            )
        except (TypeError, ValueError) as exc:
            return V3Readiness(
                "ineligible",
                service,
                posture,
                authority,
                FROZEN_V3_CONTRACT_DIGEST,
                FROZEN_V3_SOURCE_COMMIT,
                f"pre_field_signer_trust_invalid:{type(exc).__name__}",
            )
        if service != "ready":
            state = "ineligible"
        elif posture == "production" and authority == "v3":
            state = "production_ready"
        elif posture == "candidate":
            state = "rehearsal_ready"
        else:
            state = "ineligible"
        if mode == "production" and state != "production_ready":
            state = "ineligible"
        return V3Readiness(
            state,
            service,
            posture,
            authority,
            FROZEN_V3_CONTRACT_DIGEST,
            FROZEN_V3_SOURCE_COMMIT,
            pre_field_signer_trust_json=signer_trust_json,
        )

    def preselection_readiness(self) -> V3Readiness:
        """Authenticate and inspect V3 before a competition authority exists."""
        return self._readiness()

    def selector_readiness(self) -> dict[str, str]:
        """Return the judge-selector mapping without constructing another client."""
        return _selector_readiness_mapping(self.preselection_readiness())

    def readiness(self, context: PredictionExecutionContext) -> V3Readiness:
        self._validate_context(context)
        return self._readiness(context.mode)

    def _post(
        self,
        context: PredictionExecutionContext,
        operation: str,
        payload: Mapping[str, Any],
        *,
        retry_recovery: bool = False,
    ) -> dict[str, Any]:
        self._validate_context(context)
        path, expected_schema = self._POST_SCHEMAS[operation]
        encoded = _canonical_json(payload)
        request_digest = _digest_text(encoded)
        command_key = self._command_key(
            context,
            operation,
            self._semantic_identity(operation, payload),
        )
        record, created = self.command_store.begin_with_status(
            command_key=command_key,
            operation=operation,
            method="POST",
            path=path,
            request_digest=request_digest,
            request_json=encoded,
        )
        if record.state == "acknowledged":
            assert record.response is not None
            return record.response
        if record.state == "recovery_required" and not retry_recovery:
            raise V3RecoveryRequired(command_key)
        if record.state == "pending" and not created and not retry_recovery:
            self.command_store.mark_recovery_required(command_key, "preexisting_pending_command")
            raise V3RecoveryRequired(command_key)
        if record.state == "rejected":
            raise V3ClientError("V3 command was previously rejected")
        deadline_ms = payload.get("deadline_ms", 5_000)
        read_timeout = max(1.0, float(deadline_ms) / 1000 + 1.0) if isinstance(deadline_ms, int) else 6.0
        try:
            response = self._transport.request(
                "POST",
                f"{self.base_url}{path}",
                headers=self._headers(idempotency_key=command_key, action=operation),
                json=dict(payload),
                timeout=(self._connect_timeout, read_timeout),
                allow_redirects=False,
            )
        except requests.RequestException as exc:
            self.command_store.mark_recovery_required(command_key, type(exc).__name__)
            raise V3RecoveryRequired(command_key) from exc
        try:
            body = self._body(response, expected_schema)
        except V3ClientError as exc:
            if 200 <= response.status_code < 300:
                self.command_store.mark_recovery_required(command_key, "invalid_success_response")
                raise V3RecoveryRequired(command_key) from exc
            if response.status_code in {408, 429} or response.status_code >= 500:
                self.command_store.mark_recovery_required(command_key, "ambiguous_http_response")
                raise V3RecoveryRequired(command_key) from exc
            self.command_store.reject(command_key, "http_rejected")
            raise
        self.command_store.acknowledge(command_key, body)
        return body

    def retry_recovery(
        self,
        command_key: str,
        execution_context: PredictionExecutionContext,
    ) -> dict[str, Any]:
        record = self.command_store.get(command_key)
        if record.state == "acknowledged":
            assert record.response is not None
            return record.response
        if record.state != "recovery_required":
            raise V3ClientError("V3 command is not awaiting recovery")
        # Reconstruct only non-secret command facts; current canonical authority and
        # the credential are injected anew, so recovery survives process restart.
        self._validate_context(execution_context)
        expected = self._command_key(
            execution_context,
            record.operation,
            self._semantic_identity(record.operation, record.request),
        )
        if expected != command_key:
            raise V3ClientError("V3 recovery context does not bind the original command")
        return self._post(execution_context, record.operation, record.request, retry_recovery=True)

    @staticmethod
    def _command_key(
        context: PredictionExecutionContext,
        operation: str,
        semantic_identity: str,
    ) -> str:
        material = "\0".join((context.scope_id, operation, semantic_identity))
        return f"strathex-{_digest_text(material)}"

    @staticmethod
    def _semantic_identity(operation: str, payload: Mapping[str, Any]) -> str:
        """Bind retries to the upstream operation identity, not mutable request bytes."""
        if operation == "decide_approval":
            identity = {
                "snapshot_id": payload.get("snapshot_id"),
                "action": payload.get("action"),
                "selected_receipt_ids": [item.get("receipt_id") for item in payload.get("selected", ())],
                "excluded_receipt_ids": [item.get("receipt_id") for item in payload.get("excluded", ())],
            }
            if identity["snapshot_id"] is None or identity["action"] is None:
                raise V3ClientError("V3 decide_approval request lacks semantic identity fields")
            return _canonical_json(identity)
        identity_fields = {
            "open_scope": ("scope_id",),
            "synchronize_snapshot": ("entity_kind", "entity_id", "upstream_revision"),
            "freeze_round": ("round_id", "epoch_revision"),
            "close_round": ("round_id",),
            "close_scope": ("scope_id",),
            "prepare_card": ("field_id", "competitor_id", "source_revision"),
            "pre_field_forecast": (
                "tournament_id",
                "round_id",
                "forecast_set_revision",
            ),
            "assemble_field": ("field_id", "upstream_field_revision"),
            "lookup_receipt": ("request_identity",),
            "acknowledge_issue": ("upstream_issue_id",),
            "settle_result": ("issue_batch_id", "receipt_id"),
        }.get(operation)
        if identity_fields is None:
            raise V3ClientError(f"V3 operation lacks a semantic command identity: {operation}")
        identity = {name: payload.get(name) for name in identity_fields}
        if any(value is None for value in identity.values()):
            raise V3ClientError(f"V3 {operation} request lacks semantic identity fields")
        return _canonical_json(identity)

    def open_scope(self, context, payload):
        return self._post(context, "open_scope", payload)

    def synchronize_snapshot(self, context, payload):
        return self._post(context, "synchronize_snapshot", payload)

    def freeze_round(self, context, payload):
        return self._post(context, "freeze_round", payload)

    def close_round(self, context, payload):
        return self._post(context, "close_round", payload)

    def close_scope(self, context, payload):
        return self._post(context, "close_scope", payload)

    def prepare_card(self, context, payload):
        return self._post(context, "prepare_card", payload)

    def assemble_field(self, context, payload):
        return self._post(context, "assemble_field", payload)

    def lookup_receipt(self, context, payload):
        return self._post(context, "lookup_receipt", payload)

    def decide_approval(self, context, payload):
        return self._post(context, "decide_approval", payload)

    def acknowledge_issue(self, context, payload):
        return self._post(context, "acknowledge_issue", payload)

    def settle_result(self, context, payload):
        return self._post(context, "settle_result", payload)

    def approval_page(self, context: PredictionExecutionContext, **query: Any) -> dict[str, Any]:
        return self._get(
            context,
            "/v3/approvals/page",
            "strathmark-v3-approval-page-response-v1",
            query,
        )

    def approval_detail(self, context: PredictionExecutionContext, **query: Any) -> dict[str, Any]:
        return self._get(
            context,
            "/v3/approvals/detail",
            "strathmark-v3-approval-detail-response-v1",
            query,
        )

    def _get(self, context, path, expected_schema, query):
        self._validate_context(context)
        try:
            response = self._transport.request(
                "GET",
                f"{self.base_url}{path}?{urlencode(query)}",
                headers=self._headers(action="read_projection"),
                timeout=(self._connect_timeout, 5.0),
                allow_redirects=False,
            )
        except requests.RequestException as exc:
            raise V3ClientError("V3 read request failed") from exc
        return self._body(response, expected_schema)

    def pre_field_forecast(self, execution_context: PredictionExecutionContext, **request: Any) -> EngineProjection:
        competitor_names = request.pop("competitor_names", {})
        payload = {
            "schema_version": "strathmark-v3-pre-field-forecast-request-v1",
            "tournament_id": request["tournament_id"],
            "round_id": request["round_id"],
            "forecast_set_revision": int(request.get("forecast_set_revision", 1)),
            "ordered_competitor_ids": list(request["ordered_competitor_ids"]),
            "target_context": dict(request["target_context"]),
            "hard_deadline_at": request["hard_deadline_at"],
            "requested_at_utc": request["requested_at_utc"],
            "deadline_ms": int(request.get("deadline_ms", 5_000)),
        }
        response = self._post(execution_context, "pre_field_forecast", payload)
        return self._forecast_projection(
            execution_context,
            response,
            competitor_names,
            expected_tournament_id=payload["tournament_id"],
            expected_round_id=payload["round_id"],
            expected_competitor_ids=tuple(payload["ordered_competitor_ids"]),
        )

    def forecast_seeding(
        self,
        *,
        execution_context: PredictionExecutionContext,
        **request: Any,
    ) -> EngineProjection:
        """Prepare the minimum bound V3 lifecycle and return a no-mark seed forecast."""
        self._validate_context(execution_context)
        tournament_id = request["tournament_id"]
        if tournament_id != execution_context.scope_id:
            raise V3ClientError("V3 forecast tournament differs from selected scope")
        revision = int(request.get("forecast_set_revision", 1))
        self._ensure_scope_round(
            execution_context,
            request,
            round_revision=revision,
            freeze=True,
        )
        forecast_request = dict(request)
        forecast_request.pop("historical_cutoff_key", None)
        for key in (
            "round_ordinal",
            "predecessor_round_ids",
            "successor_round_ids",
            "closure_ids",
        ):
            forecast_request.pop(key, None)
        return self.pre_field_forecast(execution_context, **forecast_request)

    @staticmethod
    def _selection(execution_context: PredictionExecutionContext) -> dict[str, Any]:
        return {
            "schema_version": "strathmark-v3-competition-engine-selection-v1",
            "scope_id": execution_context.scope_id,
            "engine": "v3",
            "mode": execution_context.mode,
            "selected_by_actor_id": execution_context.selected_by_actor_id,
            "selected_at_utc": execution_context.selected_at_utc,
            "reason_code": execution_context.reason_code,
            "consumer_contract_digest": execution_context.contract_identity,
            "source_commit": execution_context.source_identity,
        }

    def _scope_opened(self, context: PredictionExecutionContext) -> bool:
        key = self._command_key(
            context,
            "open_scope",
            self._semantic_identity("open_scope", {"scope_id": context.scope_id}),
        )
        try:
            return self.command_store.get(key).state == "acknowledged"
        except KeyError:
            return False

    def _ensure_scope_round(
        self,
        execution_context: PredictionExecutionContext,
        request: Mapping[str, Any],
        *,
        round_revision: int,
        freeze: bool,
    ) -> None:
        tournament_id = request["tournament_id"]
        round_id = request["round_id"]
        if tournament_id != execution_context.scope_id:
            raise V3ClientError("V3 tournament differs from selected scope")
        observed_at = execution_context.locked_at
        cutoff = request["historical_cutoff_key"]
        deadline_ms = int(request.get("lifecycle_deadline_ms", 5_000))
        selection = self._selection(execution_context)
        common_snapshot = {
            "schema_version": "strathmark-v3-snapshot-sync-request-v1",
            "upstream_revision": int(request.get("tournament_revision", 1)),
            "tournament_id": tournament_id,
            "engine_selection": selection,
            "synchronized_at_utc": observed_at,
            "deadline_ms": deadline_ms,
        }
        self.synchronize_snapshot(
            execution_context,
            {
                **common_snapshot,
                "entity_kind": "tournament",
                "entity_id": tournament_id,
                "round_id": None,
                "snapshot": {
                    "bundle_id": self.bundle_id,
                    "historical_cutoff_key": cutoff,
                },
            },
        )
        self.synchronize_snapshot(
            execution_context,
            {
                **common_snapshot,
                "upstream_revision": round_revision,
                "entity_kind": "round",
                "entity_id": round_id,
                "round_id": round_id,
                "snapshot": {
                    "round_ordinal": int(request.get("round_ordinal", round_revision)),
                    "predecessor_round_ids": list(request.get("predecessor_round_ids", ())),
                    "successor_round_ids": list(request.get("successor_round_ids", ())),
                },
            },
        )
        if not self._scope_opened(execution_context):
            self.open_scope(
                execution_context,
                {
                    "schema_version": "strathmark-v3-scope-open-request-v1",
                    "scope_id": tournament_id,
                    "bundle_id": self.bundle_id,
                    "historical_cutoff_key": cutoff,
                    "root_round_ids": [round_id],
                    "engine_selection": selection,
                    "opened_at_utc": observed_at,
                    "deadline_ms": deadline_ms,
                },
            )
        if freeze:
            self._freeze_round(execution_context, request, round_revision=round_revision)

    def _freeze_round(
        self,
        execution_context: PredictionExecutionContext,
        request: Mapping[str, Any],
        *,
        round_revision: int,
    ) -> None:
        self.freeze_round(
            execution_context,
            {
                "schema_version": "strathmark-v3-round-freeze-request-v1",
                "round_id": request["round_id"],
                "epoch_revision": round_revision,
                "historical_cutoff_key": request["historical_cutoff_key"],
                "closure_ids": list(request.get("closure_ids", ())),
                "frozen_at_utc": execution_context.locked_at,
                "deadline_ms": int(request.get("lifecycle_deadline_ms", 5_000)),
            },
        )

    @staticmethod
    def _forecast_projection(
        context: PredictionExecutionContext,
        response: Mapping[str, Any],
        competitor_names: Mapping[str, str],
        *,
        expected_tournament_id: str,
        expected_round_id: str,
        expected_competitor_ids: tuple[str, ...],
    ) -> EngineProjection:
        try:
            receipt = json.loads(response["canonical_receipt_json"])
            if not isinstance(receipt, dict):
                raise ValueError
            content = {key: receipt[key] for key in _PRE_FIELD_RECEIPT_CONTENT_KEYS}
            receipt_digest = _receipt_content_digest(receipt, _PRE_FIELD_RECEIPT_CONTENT_KEYS)
            _validate_structural_manifest(
                receipt["manifest"],
                expected_kind="pre_field_forecast_receipt",
                expected_payload=content,
                trusted_signer_trust_json=context.pre_field_signer_trust_json or "",
            )
            snapshot = receipt["snapshot"]
            authority = snapshot["engine_authority"]
            forecasts = receipt["forecasts"]
            if (
                receipt.get("purpose") != "pre_field_seeding_only"
                or receipt.get("issued_mark") is not False
                or receipt.get("receipt_digest") != response["receipt_digest"]
                or receipt_digest != response["receipt_digest"]
                or response.get("purpose") != "pre_field_seeding_only"
                or response.get("issued_mark") is not False
                or snapshot.get("tournament_id") != expected_tournament_id
                or snapshot.get("round_id") != expected_round_id
                or tuple(snapshot.get("ordered_competitor_ids", ())) != expected_competitor_ids
                or authority.get("scope_id") != context.scope_id
                or authority.get("engine") != "v3"
                or authority.get("mode") != context.mode
                or authority.get("selection_digest") != _digest_text(_canonical_json(V3HttpClient._selection(context)))
                or authority.get("consumer_contract_digest") != context.contract_identity
                or authority.get("source_commit") != context.source_identity
                or not isinstance(forecasts, list)
                or tuple(item.get("competitor_id") for item in forecasts) != expected_competitor_ids
                or any("mark" in item for item in forecasts)
            ):
                raise ValueError
            rows = [
                {
                    "name": competitor_names.get(item["competitor_id"], item["competitor_id"]),
                    "competitor_id": item["competitor_id"],
                    "predicted_time": int(item["p50_seed_time_ms"]) / 1000,
                    "method_used": "V3 Pre-field Forecast",
                    "engine_version": "3.0.0",
                    "selected_engine": context.selected_engine,
                    "returned_engine": "v3",
                    "engine_mode": context.mode,
                    "receipt_digest": response["receipt_digest"],
                    "forecast_set_id": response["forecast_set_id"],
                    "forecast_digest": item["forecast_digest"],
                    "forecast_basis": item["basis_kind"],
                    "mark_origin": "not_issued_pre_field_forecast",
                }
                for item in forecasts
            ]
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise V3ClientError("V3 pre-field receipt is incomplete or malformed") from exc
        return rows

    def __call__(self, *, execution_context: PredictionExecutionContext, **request: Any) -> EngineProjection:
        if "tournament_id" not in request:
            payload = {
                "schema_version": "strathmark-v3-field-assembly-request-v1",
                "field_id": request["field_id"],
                "upstream_field_revision": request["upstream_field_revision"],
                "ordered_competitor_ids": list(request["ordered_competitor_ids"]),
                "deadline_ms": int(request.get("deadline_ms", 5_000)),
            }
            response = self.assemble_field(execution_context, payload)
            return self._projection(
                execution_context,
                response,
                request.get("competitor_names", {}),
                expected_field_id=payload["field_id"],
                expected_competitor_ids=tuple(payload["ordered_competitor_ids"]),
            )
        round_revision = int(request.get("epoch_revision", 1))
        self._ensure_scope_round(
            execution_context,
            request,
            round_revision=round_revision,
            freeze=False,
        )
        selection = self._selection(execution_context)
        self.synchronize_snapshot(
            execution_context,
            {
                "schema_version": "strathmark-v3-snapshot-sync-request-v1",
                "entity_kind": "field",
                "entity_id": request["field_id"],
                "upstream_revision": int(request["upstream_field_revision"]),
                "tournament_id": request["tournament_id"],
                "round_id": request["round_id"],
                "snapshot": {
                    "competitor_ids": list(request["ordered_competitor_ids"]),
                    "target_context": dict(request["target_context"]),
                    "stand_ids": list(request["stand_ids"]),
                },
                "engine_selection": selection,
                "synchronized_at_utc": request["requested_at_utc"],
                "deadline_ms": int(request.get("deadline_ms", 5_000)),
            },
        )
        self._freeze_round(execution_context, request, round_revision=round_revision)
        context_digest = _digest_text(_canonical_json(request["target_context"]))
        # Keep card commands serial until both the injected transport and durable
        # command store expose an explicit thread-safety contract.  Parallelizing
        # this loop would otherwise trade a speculative latency win for ambiguous
        # command ownership and non-deterministic recovery ordering.
        for competitor_id in request["ordered_competitor_ids"]:
            preparation_deadline_ms = self._remaining_deadline_ms(
                request["hard_deadline_at"],
                maximum_ms=int(request.get("preparation_deadline_ms", 60_000)),
            )
            self.prepare_card(
                execution_context,
                {
                    "schema_version": "strathmark-v3-card-preparation-request-v1",
                    "tournament_id": request["tournament_id"],
                    "round_id": request["round_id"],
                    "field_id": request["field_id"],
                    "competitor_id": competitor_id,
                    "source_revision": int(request["upstream_field_revision"]),
                    "target_context_digest": context_digest,
                    "deadline_ms": preparation_deadline_ms,
                },
            )
        assembly_deadline_ms = self._remaining_deadline_ms(
            request["hard_deadline_at"],
            maximum_ms=int(request.get("deadline_ms", 5_000)),
        )
        payload = {
            "schema_version": "strathmark-v3-field-assembly-request-v1",
            "field_id": request["field_id"],
            "upstream_field_revision": request["upstream_field_revision"],
            "ordered_competitor_ids": list(request["ordered_competitor_ids"]),
            "deadline_ms": assembly_deadline_ms,
        }
        response = self.assemble_field(execution_context, payload)
        return self._projection(
            execution_context,
            response,
            request.get("competitor_names", {}),
            expected_field_id=payload["field_id"],
            expected_competitor_ids=tuple(payload["ordered_competitor_ids"]),
        )

    @staticmethod
    def _projection(
        context,
        response,
        competitor_names,
        *,
        expected_field_id,
        expected_competitor_ids,
    ):
        try:
            receipt = json.loads(response["canonical_receipt_json"])
            if not isinstance(receipt, dict) or receipt.get("receipt_id") != response["receipt_id"]:
                raise ValueError
            content_digest = _receipt_content_digest(receipt, _FIELD_RECEIPT_CONTENT_KEYS)
            if (
                receipt.get("content_digest") != response["receipt_digest"]
                or content_digest != response["receipt_digest"]
                or receipt.get("field_id") != expected_field_id
                or tuple(receipt.get("ordered_competitor_ids", ())) != expected_competitor_ids
            ):
                raise ValueError
            returned_authority = receipt.get("engine_authority")
            if (
                not isinstance(returned_authority, dict)
                or returned_authority.get("scope_id") != context.scope_id
                or returned_authority.get("engine") != "v3"
                or returned_authority.get("mode") != context.mode
                or returned_authority.get("selection_digest")
                != _digest_text(_canonical_json(V3HttpClient._selection(context)))
                or returned_authority.get("consumer_contract_digest") != context.contract_identity
                or returned_authority.get("source_commit") != context.source_identity
            ):
                raise ValueError
            marks = {item["competitor_id"]: item["mark"] for item in receipt["marks"]}
            expected: dict[str, int] = {}
            for section in receipt.get("sections", []):
                if section.get("kind") == "optimizer_frontier" and section.get("payload_type") == "inline":
                    value = json.loads(section["payload"]["canonical_json"])
                    expected = {item[0]: item[1] for item in value.get("expected_times_ms", [])}
            ordered = receipt["ordered_competitor_ids"]
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise V3ClientError("V3 field receipt is incomplete or malformed") from exc
        rows = []
        for competitor_id in ordered:
            if competitor_id not in marks or competitor_id not in expected:
                raise V3ClientError("V3 field receipt lacks complete-field marks or expected times")
            rows.append(
                {
                    "name": competitor_names.get(competitor_id, competitor_id),
                    "competitor_id": competitor_id,
                    "mark": marks[competitor_id],
                    "predicted_time": expected[competitor_id] / 1000,
                    "method_used": "V3 Ensemble",
                    "engine_version": "3.0.0",
                    "selected_engine": context.selected_engine,
                    "returned_engine": "v3",
                    "engine_mode": context.mode,
                    "receipt_id": response["receipt_id"],
                    "receipt_digest": response["receipt_digest"],
                    "warnings": list(receipt.get("warning_codes", [])),
                    "bundles": list(receipt.get("bundles", [])),
                }
            )
        return rows


def _runtime_credential_provider(
    environ: Mapping[str, str],
) -> CredentialProvider:
    environment_reference = str(environ.get("STRATHMARK_V3_CREDENTIAL_ENV", "")).strip()
    keyring_service = str(environ.get("STRATHMARK_V3_CREDENTIAL_KEYRING_SERVICE", "")).strip()
    keyring_account = str(environ.get("STRATHMARK_V3_CREDENTIAL_KEYRING_ACCOUNT", "")).strip()
    if environment_reference:
        if keyring_service or keyring_account:
            raise V3RuntimeConfigurationError("Configure exactly one V3 credential reference mechanism")
        if _ENVIRONMENT_NAME.fullmatch(environment_reference) is None:
            raise V3RuntimeConfigurationError("The V3 credential environment reference is invalid")

        def from_environment() -> str:
            return str(environ.get(environment_reference, ""))

        if not from_environment():
            raise V3RuntimeConfigurationError("The referenced V3 service credential is unavailable")
        return from_environment
    if keyring_service and keyring_account:
        try:
            import keyring
        except ImportError as exc:
            raise V3RuntimeConfigurationError("The configured OS credential provider is unavailable") from exc

        def from_keyring() -> str:
            return str(keyring.get_password(keyring_service, keyring_account) or "")

        if not from_keyring():
            raise V3RuntimeConfigurationError("The referenced V3 service credential is unavailable")
        return from_keyring
    raise V3RuntimeConfigurationError("No V3 service credential reference is configured")


def build_v3_client(
    *,
    environ: Mapping[str, str] | None = None,
    transport: HttpTransport | None = None,
) -> V3HttpClient:
    """Construct the runtime client only from explicit, reviewed references."""
    runtime = os.environ if environ is None else environ
    base_url = str(runtime.get("STRATHMARK_V3_BASE_URL", "")).strip()
    command_database = str(runtime.get("STRATHEX_V3_COMMAND_DB", "")).strip()
    bundle_id = str(runtime.get("STRATHMARK_V3_BUNDLE_ID", "")).strip()
    contract_digest = str(runtime.get("STRATHMARK_V3_CONTRACT_DIGEST", "")).strip()
    source_commit = str(runtime.get("STRATHMARK_V3_SOURCE_COMMIT", "")).strip()
    if not base_url or not command_database or not bundle_id:
        raise V3RuntimeConfigurationError(
            "The V3 loopback URL, durable command database, and reviewed bundle must be configured"
        )
    if contract_digest != FROZEN_V3_CONTRACT_DIGEST:
        raise V3RuntimeConfigurationError("The configured V3 consumer contract does not match the reviewed pin")
    if source_commit != FROZEN_V3_SOURCE_COMMIT:
        raise V3RuntimeConfigurationError("The configured V3 source does not match the reviewed pin")
    try:
        credential_provider = _runtime_credential_provider(runtime)
        return V3HttpClient(
            base_url=base_url,
            credential_provider=credential_provider,
            command_store=V3CommandStore(Path(command_database)),
            transport=transport,
            bundle_id=bundle_id,
        )
    except (OSError, TypeError, ValueError) as exc:
        raise V3RuntimeConfigurationError("The configured V3 runtime could not be constructed") from exc


def _selector_readiness_mapping(readiness: V3Readiness) -> dict[str, Any]:
    if readiness.state == "rehearsal_ready":
        message = "Authenticated STRATHMARK V3 candidate is available for rehearsal."
    elif readiness.state == "production_ready":
        message = "Authenticated STRATHMARK V3 is the verified production authority."
    elif readiness.state == "ineligible":
        message = "Authenticated STRATHMARK V3 is not eligible for selection."
    else:
        return {
            "status": "status_failed",
            "message": "Authenticated STRATHMARK V3 readiness could not be verified.",
        }
    result: dict[str, Any] = {
        "status": readiness.state,
        "message": message,
        "contract_identity": readiness.contract_digest,
        "source_identity": readiness.source_commit,
    }
    if readiness.pre_field_signer_trust_json is not None:
        result["pre_field_signer_trust"] = json.loads(readiness.pre_field_signer_trust_json)
    return result


def get_v3_readiness(
    *,
    environ: Mapping[str, str] | None = None,
    transport: HttpTransport | None = None,
) -> dict[str, Any]:
    """Return the exact fail-closed mapping consumed by the U6 selector UI."""
    try:
        client = build_v3_client(environ=environ, transport=transport)
    except V3RuntimeConfigurationError:
        return {
            "status": "ineligible",
            "message": "STRATHMARK V3 runtime is not configured with reviewed pins and a credential reference.",
        }
    return _selector_readiness_mapping(client.preselection_readiness())


__all__ = [
    "FROZEN_V3_CONTRACT_DIGEST",
    "FROZEN_V3_CONTRACT_VERSION",
    "FROZEN_V3_SOURCE_COMMIT",
    "V3ClientError",
    "V3HttpClient",
    "V3Readiness",
    "V3RecoveryRequired",
    "V3RuntimeConfigurationError",
    "build_v3_client",
    "get_v3_readiness",
]
