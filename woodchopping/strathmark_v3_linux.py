"""Signed subprocess consumer for the separate Linux competition lifecycle."""

from __future__ import annotations

import base64
import hashlib
import json
import math
import os
import subprocess
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

from woodchopping.strathmark_v3_client import V3ClientError, V3RecoveryRequired, V3RuntimeConfigurationError
from woodchopping.v3_authority_store import V3CommandStore

LINUX_PROTOCOL = "strathmark.v3-linux-competition.v1"
FROZEN_LINUX_SOURCE_COMMIT = "d0247945e2218addc0cbe5805f906456df0d2afe"
FROZEN_LINUX_IMPLEMENTATION_DIGEST = "8b2225b09b0faae817dea77670fdd9f834ee0fc31f58f89ec415b120ba86581e"
# Frozen separately from the Windows V7 service and the earlier preview profile.
LINUX_CONTRACT_DIGEST = "162a5317adce4c2efd037d50e9d0239a49dc849dfaa365d935356a6240bc455e"


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def validate_local_trust(value):
    if not isinstance(value, dict) or set(value) != {"key_id", "key_class", "provider", "public_key_der_b64"}:
        raise V3ClientError("Linux installation signing identity is incomplete")
    if value["key_class"] != "linux_installation" or value["provider"] != "linux_owner_private_p256_sha256":
        raise V3ClientError("Linux competition requires its persistent installation signer")
    try:
        key = serialization.load_der_public_key(base64.b64decode(value["public_key_der_b64"], validate=True))
    except (ValueError, TypeError) as error:
        raise V3ClientError("Linux installation public key is invalid") from error
    if not isinstance(key, ec.EllipticCurvePublicKey) or not isinstance(key.curve, ec.SECP256R1):
        raise V3ClientError("Linux installation public key must be P-256")
    if value["key_id"] != "integrity-key:linux-" + digest({"public_key": value["public_key_der_b64"]}):
        raise V3ClientError("Linux installation public key identity differs")
    return key


class LinuxV3Competition:
    pre_field_requires_local_roster = True
    requires_explicit_issue = True

    def __init__(self, *, python, ml_bundle, workbook, runtime_root, command_store, backup_dir=None):
        self.python = Path(python).expanduser().absolute()
        self.ml_bundle = Path(ml_bundle).expanduser().absolute()
        self.workbook = Path(workbook).resolve(strict=True)
        self.runtime_root = Path(runtime_root).expanduser().absolute()
        self.command_store = command_store
        self.backup_dir = None if backup_dir is None else Path(backup_dir).resolve(strict=True)
        if os.environ.get("STRATHEX_TEST_DB") != "1" and (
            self.backup_dir is None
            or not self.backup_dir.is_dir()
            or self.backup_dir.stat().st_dev == self.workbook.stat().st_dev
        ):
            raise V3RuntimeConfigurationError(
                "Linux operator competitions require recovery on an independent filesystem"
            )
        if not self.python.is_file():
            raise V3RuntimeConfigurationError("separate Linux V3 Python is missing")
        self.identity = self._run("status" if self.runtime_root.exists() else "init")
        self._validate_identity(self.identity)
        self.source_identity = self.identity["source_identity"]
        self.competition_sources = self.identity.get("competition_sources", {})
        self.trust = self.identity["installation_identity"]
        self.public_key = validate_local_trust(self.trust)

    @staticmethod
    def _validate_identity(identity):
        if (
            identity.get("source_digest") != FROZEN_LINUX_IMPLEMENTATION_DIGEST
            or identity.get("protocol") != LINUX_PROTOCOL
            or identity.get("contract_digest") != LINUX_CONTRACT_DIGEST
            or identity.get("purpose") != "competition_lifecycle"
            or identity.get("mode") != "local"
            or identity.get("windows_production_qualified") is not False
        ):
            raise V3RuntimeConfigurationError("Linux lifecycle protocol differs from the reviewed consumer")
        material = {
            key: identity[key]
            for key in (
                "source_digest",
                "package_version",
                "formula_digest",
                "ml_bundle_digest",
                "installation_identity",
            )
        }
        if digest(material) != identity.get("source_identity"):
            raise V3RuntimeConfigurationError("Linux source, model, or installation identity differs")
        validate_local_trust(material["installation_identity"])

    def _run(self, operation, envelope=None):
        environment = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith(("STRATHMARK_", "STRATHEX_", "PYTHONPATH", "PYTHONHOME"))
        }
        arguments = [
            str(self.python),
            "-I",
            "-m",
            "strathmark.v3.linux_lifecycle",
            operation,
            "--runtime-root",
            str(self.runtime_root),
            "--ml-bundle",
            str(self.ml_bundle),
        ]
        if self.backup_dir is not None:
            arguments.extend(["--backup-dir", str(self.backup_dir)])
        try:
            result = subprocess.run(
                arguments,
                input=None if envelope is None else encoded(envelope),
                capture_output=True,
                timeout=150,
                env=environment,
                cwd=str(self.runtime_root.parent),
            )
        except (OSError, subprocess.SubprocessError) as error:
            raise V3ClientError("Linux V3 subprocess did not return a confirmed response") from error
        if result.returncode:
            raise V3ClientError(
                result.stderr.decode("utf-8", errors="replace").strip()[-2000:] or "Linux V3 command failed"
            )
        if len(result.stdout) > 20_000_000:
            raise V3ClientError("Linux V3 response exceeds capacity")
        try:
            value = json.loads(result.stdout)
        except ValueError as error:
            raise V3ClientError("Linux V3 response is malformed") from error
        if not isinstance(value, dict):
            raise V3ClientError("Linux V3 response must be an object")
        return value

    def selector_readiness(self):
        current = self._run("status")
        self._validate_identity(current)
        if current["source_identity"] != self.source_identity or current.get("numeric_available") is not True:
            return {
                "status": "ineligible",
                "message": "Verified Formula and ML are required for a new Linux competition.",
            }
        return {
            "status": "local_ready",
            "runtime_profile": LINUX_PROTOCOL,
            "contract_identity": LINUX_CONTRACT_DIGEST,
            "source_identity": self.source_identity,
            "pre_field_signer_trust": self.trust,
            "message": "Linux competition workflow available: Formula + trained ML; LLM council unavailable. Judge review and separate issue confirmation required.",
        }

    def _context(self, context):
        if (
            context.selected_engine != "v3"
            or context.mode != "local"
            or context.contract_identity != LINUX_CONTRACT_DIGEST
        ):
            raise V3ClientError("request differs from the selected Linux competition engine")
        if context.source_identity != self.competition_sources.get(context.scope_id, self.source_identity):
            raise V3ClientError("competition source identity differs from the retained installation")
        trust = json.loads(context.pre_field_signer_trust_json or "null")
        if trust != self.trust:
            raise V3ClientError("competition signer changed after selection")
        return {
            key: getattr(context, key)
            for key in (
                "scope_id",
                "selected_engine",
                "mode",
                "contract_identity",
                "source_identity",
                "selected_by_actor_id",
                "locked_at",
            )
        }

    def _verify(self, operation, envelope, result):
        expected = {
            "protocol": LINUX_PROTOCOL,
            "operation": operation,
            "request_digest": digest(envelope),
            "response_digest": digest(result.get("response")),
        }
        if any(result.get(key) != value for key, value in expected.items()):
            raise V3ClientError("Linux response does not bind the exact command")
        try:
            manifest = result["manifest"]
            body_json = manifest["body_json"]
            body = json.loads(body_json)
            if (
                encoded(body).decode() != body_json
                or digest(body) != manifest["body_digest"]
                or manifest["schema_version"] != "strathmark-v3-signed-manifest-v1"
                or manifest["kind"] != "linux_competition_response"
                or body["kind"] != manifest["kind"]
                or body["key_id"] != self.trust["key_id"]
                or manifest["key_id"] != self.trust["key_id"]
                or body["algorithm"] != "ecdsa-p256-sha256"
                or body["schema_version"] != "strathmark-v3-integrity-body-v1"
                or body["payload"] != expected
            ):
                raise ValueError("manifest identity differs")
            self.public_key.verify(
                base64.b64decode(manifest["signature_der_b64"], validate=True),
                body_json.encode(),
                ec.ECDSA(hashes.SHA256()),
            )
        except Exception as error:
            raise V3ClientError("Linux competition response signature is invalid") from error
        if not isinstance(result["response"], dict):
            raise V3ClientError("Linux operation response is malformed")
        return result["response"]

    def _command(self, context, operation, payload, *, semantic=None, retry=False):
        frozen = self._context(context)
        semantic = digest(payload) if semantic is None else semantic
        command_key = "strathex-linux-" + digest(
            {"scope": context.scope_id, "operation": operation, "semantic": semantic}
        )
        envelope = {"command_id": command_key, "context": frozen, "payload": payload}
        read_only = operation in {"approval_page", "approval_detail", "lookup"}
        if read_only:
            return self._verify(operation, envelope, self._run(operation, envelope))
        record, created = self.command_store.begin_with_status(
            command_key=command_key,
            operation=operation,
            method="LOCAL",
            path=operation,
            request_digest=digest(envelope),
            request_json=encoded(envelope).decode(),
        )
        if record.state == "acknowledged":
            return record.response
        if not created and not retry:
            raise V3RecoveryRequired(command_key)
        try:
            response = self._verify(operation, envelope, self._run(operation, envelope))
        except V3ClientError as error:
            self.command_store.mark_recovery_required(command_key, "local_outcome_unconfirmed")
            raise V3RecoveryRequired(command_key) from error
        self.command_store.acknowledge(command_key, response)
        return response

    def retry_recovery(self, command_key, execution_context):
        record = self.command_store.get(command_key)
        envelope = record.request
        if envelope["context"] != self._context(execution_context) or envelope["command_id"] != command_key:
            raise V3ClientError("recovery context differs from the retained command")
        try:
            response = self._verify(record.operation, envelope, self._run(record.operation, envelope))
        except V3ClientError as error:
            raise V3RecoveryRequired(command_key) from error
        self.command_store.acknowledge(command_key, response)
        return response

    def __call__(self, *, execution_context, **request):
        return self._calculate(execution_context, request, forecast_only=False)

    def forecast_seeding(self, *, execution_context, **request):
        return self._calculate(execution_context, request, forecast_only=True)

    def _calculate(self, context, request, *, forecast_only):
        roster = request["competitors_df"]
        if "competitor_id" not in roster:
            raise V3ClientError("Linux V3 needs stable competitor IDs")
        ordinal = request.get("round_ordinal", 1)
        if ordinal > 1:
            from datetime import datetime, timezone

            group = request["epoch_group_id"]
            semantic = f"advance:{group}:{ordinal}"
            key = "strathex-linux-" + digest({"scope": context.scope_id, "operation": "advance", "semantic": semantic})
            try:
                advance_payload = self.command_store.get(key).request["payload"]
            except KeyError:
                advance_payload = {
                    "round_ordinal": ordinal,
                    "epoch_group_id": group,
                    "closed_at_utc": datetime.now(timezone.utc)
                    .isoformat(timespec="milliseconds")
                    .replace("+00:00", "Z"),
                }
            self._command(
                context,
                "advance",
                advance_payload,
                semantic=semantic,
            )
        as_of = str(request.get("prediction_as_of") or context.locked_at[:10])[:10]
        payload = {
            "workbook": str(self.workbook),
            "cutoff_at_utc": f"{as_of}T00:00:00.000Z",
            "round_id": request["round_id"],
            "round_ordinal": ordinal,
            "epoch_group_id": request["epoch_group_id"],
            "predecessor_round_ids": [],
            "competitor_ids": roster["competitor_id"].astype(str).tolist(),
            "upstream_competitor_ids": list(request["ordered_competitor_ids"]),
            "target_context": dict(request["target_context"]),
        }
        if not forecast_only:
            payload.update(
                field_kind=request.get("field_kind", "handicap"),
                field_id=request["field_id"],
                upstream_field_revision=request["upstream_field_revision"],
                stand_ids=list(request["stand_ids"]),
                ceiling=request.get("ceiling", 180),
            )
        operation = "forecast" if forecast_only else "field"
        result = self._command(
            context,
            operation,
            payload,
            semantic=digest(
                {
                    "round": payload["round_id"],
                    "field": payload.get("field_id"),
                    "revision": payload.get("upstream_field_revision", 1),
                    "roster": payload["competitor_ids"],
                }
            ),
        )
        check = dict(result)
        receipt_digest = check.pop("receipt_digest", None)
        if (
            digest(check) != receipt_digest
            or result.get("protocol") != LINUX_PROTOCOL
            or result.get("selection") != self._context(context)
            or result.get("round_id") != payload["round_id"]
            or result.get("competitor_ids") != payload["upstream_competitor_ids"]
            or result.get("local_competitor_ids") != payload["competitor_ids"]
            or result.get("issued_mark") is not False
        ):
            raise V3ClientError("Linux receipt differs from the selected scope or exact roster")
        forecasts = result["numeric"]["forecasts"]
        if len(forecasts) != len(roster):
            raise V3ClientError("Linux receipt has incomplete numeric forecasts")
        marks = result["numeric"].get("marks")
        if forecast_only and marks is not None:
            raise V3ClientError("seeding forecast cannot contain marks")
        if not forecast_only and (
            not isinstance(marks, list)
            or len(marks) != len(roster)
            or min(marks) != 3
            or any(type(mark) is not int or not 3 <= mark <= payload["ceiling"] for mark in marks)
            or result.get("field_id") != payload["field_id"]
            or result.get("stand_ids") != payload["stand_ids"]
            or result.get("upstream_field_revision") != payload["upstream_field_revision"]
        ):
            raise V3ClientError("Linux field marks or stand bindings are invalid")
        rows = []
        for index, item in enumerate(forecasts):
            time, spread = item["predicted_time_ms"] / 1000, float(item["std_dev_seconds"])
            if (
                not math.isfinite(time)
                or time <= 0
                or not math.isfinite(spread)
                or spread <= 0
                or item["local_competitor_id"] != payload["competitor_ids"][index]
            ):
                raise V3ClientError("Linux numeric forecast is invalid")
            row = {
                "name": str(roster.iloc[index]["competitor_name"]),
                "competitor_id": payload["upstream_competitor_ids"][index],
                "local_competitor_id": payload["competitor_ids"][index],
                "predicted_time": time,
                "std_dev": spread,
                "engine_version": self.identity["package_version"],
                "selected_engine": "v3",
                "returned_engine": "v3",
                "engine_mode": "local",
                "method_used": "V3 Formula + trained ML",
                "confidence": "JUDGE REVIEW REQUIRED",
                "explanation": "Local Linux competition policy; trained Formula/ML ensemble, LLM council unavailable.",
                "mark_origin": "linux_competition_proposal",
                "receipt_id": result["receipt_id"],
                "receipt_digest": receipt_digest,
                "epoch_digest": result["numeric"]["epoch_digest"],
                "round_id": payload["round_id"],
                "warnings": ["LLM council unavailable; explicit review required"],
            }
            if not forecast_only:
                row.update(
                    mark=marks[index],
                    field_id=payload["field_id"],
                    upstream_field_revision=payload["upstream_field_revision"],
                )
            rows.append(row)
        return rows

    def approval_page(self, context, *, tournament_id, offset=0, limit=100):
        if tournament_id != context.scope_id:
            raise V3ClientError("approval scope differs")
        return self._command(context, "approval_page", {"offset": offset, "limit": limit})

    def approval_detail(self, context, *, tournament_id, snapshot_id, receipt_id):
        if tournament_id != context.scope_id:
            raise V3ClientError("approval detail scope differs")
        return self._command(context, "approval_detail", {"snapshot_id": snapshot_id, "receipt_id": receipt_id})

    def decide_approval(self, context, payload):
        return self._command(context, "approve", payload)

    def acknowledge_issue(self, context, payload):
        return self._command(context, "issue", payload, semantic=payload["upstream_issue_id"])

    def settle_result(self, context, payload):
        return self._command(
            context,
            "settle",
            payload,
            semantic=payload["receipt_id"] + ":" + str(max(item["source_revision"] for item in payload["results"])),
        )

    def recover_result_request(self, context, receipt_id, revision=1):
        semantic = receipt_id + ":" + str(revision)
        key = "strathex-linux-" + digest({"scope": context.scope_id, "operation": "settle", "semantic": semantic})
        try:
            record = self.command_store.get(key)
        except KeyError:
            return None
        if record.request["context"] != self._context(context):
            raise V3ClientError("saved settlement differs from the retained competition")
        return record.request["payload"]

    def correct_result(self, context, payload):
        return self._command(
            context,
            "correct",
            payload,
            semantic=payload["receipt_id"] + ":" + str(max(item["source_revision"] for item in payload["results"])),
        )

    def validate_mark_rows(self, context, rows):
        grouped = {}
        for row in rows:
            grouped.setdefault(row["receipt_id"], []).append(row)
        for receipt_id, field_rows in grouped.items():
            receipt = self._command(context, "lookup", {"receipt_id": receipt_id})
            marks = dict(zip(receipt["competitor_ids"], receipt["numeric"]["marks"], strict=True))
            local_ids = dict(zip(receipt["competitor_ids"], receipt["local_competitor_ids"], strict=True))
            if set(row["competitor_id"] for row in field_rows) != set(marks) or any(
                row.get("mark") != marks.get(row["competitor_id"])
                or row.get("local_competitor_id") != local_ids.get(row["competitor_id"])
                or row.get("receipt_digest") != receipt["receipt_digest"]
                for row in field_rows
            ):
                raise V3ClientError(
                    "displayed marks differ from the signed field; restore the original sheet or create a new unissued field revision"
                )

    def close_round(self, context, payload):
        return self._command(context, "close_round", payload, semantic=payload["round_id"])

    def close_scope(self, context, payload):
        return self._command(context, "close_scope", payload, semantic=context.scope_id)


def build_linux_v3_competition(runtime):
    names = (
        "STRATHEX_V3_LOCAL_PYTHON",
        "STRATHEX_V3_LOCAL_ML_BUNDLE",
        "STRATHEX_WORKBOOK",
        "STRATHEX_V3_LOCAL_RUNTIME_ROOT",
        "STRATHEX_V3_COMMAND_DB",
    )
    if any(not runtime.get(name) for name in names):
        raise V3RuntimeConfigurationError(
            "Linux lifecycle requires separate Python, model, workbook, runtime authority, and command database"
        )
    if not runtime.get("STRATHEX_V3_LOCAL_BACKUP_DIR") and os.environ.get("STRATHEX_TEST_DB") != "1":
        raise V3RuntimeConfigurationError("Linux operator competitions require an independent recovery directory")
    return LinuxV3Competition(
        python=runtime[names[0]],
        ml_bundle=runtime[names[1]],
        workbook=runtime[names[2]],
        runtime_root=runtime[names[3]],
        command_store=V3CommandStore(runtime[names[4]]),
        backup_dir=runtime.get("STRATHEX_V3_LOCAL_BACKUP_DIR"),
    )
