"""Explicit local Linux numeric preview profile, isolated from the V2 library.

The subprocess executes installed V3 assessors and optimizer with a verified ML
bundle. This profile has its own contract; it never represents itself as the V7
service or authorizes approval, issue, results, or settlement.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Mapping

from woodchopping.engine_selection import PredictionExecutionContext
from woodchopping.strathmark_v3_client import V3ClientError, V3RuntimeConfigurationError

LOCAL_V3_PROTOCOL = "strathmark.v3-linux-numeric-candidate.v1"
LOCAL_V3_CONTRACT_DIGEST = "9db1f82e2fa6d9aa4bea4b5751652909f5b114aa4b6b3ae93a640c3a6b3d6b67"


class LocalV3Candidate:
    pre_field_requires_local_roster = True

    def __init__(self, *, python: Path, ml_bundle: Path, workbook: Path, snapshot_root: Path):
        # Resolving a venv's Python symlink would invoke the base interpreter and
        # discard the separately installed V3 environment.
        self.python = python.expanduser().absolute()
        if not self.python.is_file():
            raise FileNotFoundError(self.python)
        self.ml_bundle = ml_bundle.resolve(strict=True)
        self.workbook = workbook.resolve(strict=True)
        self.snapshot_root = snapshot_root.resolve()
        self._identity = self._run("status")
        if (
            self._identity.get("protocol") != LOCAL_V3_PROTOCOL
            or self._identity.get("contract_digest") != LOCAL_V3_CONTRACT_DIGEST
            or self._identity.get("purpose") != "numeric_preview_only"
            or self._identity.get("production_ready") is not False
            or self._identity.get("assessors")
            != {"formula": "available", "ml": "available", "llm_council": "unavailable"}
        ):
            raise V3RuntimeConfigurationError("the installed local V3 candidate protocol or assessor identity differs")
        self.source_identity = self._source_identity(self._identity)

    @staticmethod
    def _source_identity(identity):
        return hashlib.sha256(
            json.dumps(
                {
                    key: identity[key]
                    for key in ("source_digest", "formula_digest", "ml_bundle_digest", "package_version")
                },
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()

    def _run(self, operation: str, payload: Mapping[str, Any] | None = None) -> dict:
        child_environment = {
            key: value
            for key, value in os.environ.items()
            if not key.startswith(("STRATHMARK_", "STRATHEX_", "PYTHONPATH", "PYTHONHOME"))
        }
        completed = subprocess.run(
            [
                str(self.python),
                "-I",
                "-m",
                "strathmark.v3.linux_candidate",
                operation,
                "--ml-bundle",
                str(self.ml_bundle),
            ],
            input=None if payload is None else json.dumps(payload),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=120,
            cwd=str(self.ml_bundle),
            env=child_environment,
        )
        if completed.returncode:
            raise V3ClientError(completed.stderr.strip() or "local V3 candidate failed")
        if len(completed.stdout.encode("utf-8")) > 20_000_000:
            raise V3ClientError("local V3 candidate response exceeds its byte limit")
        try:
            result = json.loads(completed.stdout)
        except (TypeError, ValueError) as error:
            raise V3ClientError("local V3 candidate returned malformed output") from error
        if not isinstance(result, dict):
            raise V3ClientError("local V3 candidate returned a malformed object")
        return result

    def selector_readiness(self) -> dict:
        identity = self._run("status")
        if self._source_identity(identity) != self.source_identity:
            raise V3ClientError("local V3 source or ML bundle changed after configuration")
        return {
            "status": "numeric_preview_ready",
            "runtime_profile": LOCAL_V3_PROTOCOL,
            "message": "Linux Formula + trained ML are runnable. LLM council is unavailable. Approval, issue, and results require the full V7 runtime.",
            "contract_identity": LOCAL_V3_CONTRACT_DIGEST,
            "source_identity": self.source_identity,
        }

    def _snapshot(self, context: PredictionExecutionContext, cutoff: str) -> Path:
        folder = self.snapshot_root / hashlib.sha256(context.scope_id.encode()).hexdigest()
        folder.mkdir(parents=True, mode=0o700, exist_ok=True)
        path, manifest_path = folder / "history.xlsx", folder / "snapshot.json"
        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text("utf-8"))
            if (
                manifest.get("cutoff_at_utc") != cutoff
                or manifest.get("scope_id") != context.scope_id
                or manifest.get("source_identity") != context.source_identity
            ):
                raise V3ClientError("local V3 scope snapshot differs from its frozen selection or cutoff")
        else:
            if path.exists():
                raise V3ClientError("interrupted local V3 snapshot needs recovery before numeric work")
            source_digest = hashlib.sha256(self.workbook.read_bytes()).hexdigest()
            shutil.copyfile(self.workbook, path)
            if (
                hashlib.sha256(path.read_bytes()).hexdigest() != source_digest
                or hashlib.sha256(self.workbook.read_bytes()).hexdigest() != source_digest
            ):
                raise V3ClientError("workbook changed while freezing the local V3 scope")
            path.chmod(0o444)
            manifest = {
                "scope_id": context.scope_id,
                "source_identity": context.source_identity,
                "cutoff_at_utc": cutoff,
                "source_workbook": str(self.workbook),
                "sha256": source_digest,
            }
            with manifest_path.open("x", encoding="utf-8") as stream:
                json.dump(manifest, stream, sort_keys=True, indent=2)
        if hashlib.sha256(path.read_bytes()).hexdigest() != manifest["sha256"]:
            raise V3ClientError("local V3 frozen workbook digest differs")
        return path

    def __call__(self, *, execution_context: PredictionExecutionContext, **request):
        return self._calculate(execution_context, request, forecast_only=False)

    def forecast_seeding(self, *, execution_context: PredictionExecutionContext, **request):
        return self._calculate(execution_context, request, forecast_only=True)

    def _calculate(self, context, request, *, forecast_only):
        if (
            context.selected_engine != "v3"
            or context.mode != "rehearsal"
            or context.contract_identity != LOCAL_V3_CONTRACT_DIGEST
            or context.source_identity != self.source_identity
        ):
            raise V3ClientError("local V3 request differs from the selected numeric preview authority")
        self.selector_readiness()
        roster = request["competitors_df"]
        if "competitor_id" not in roster:
            raise V3ClientError("local V3 requires stable competitor IDs")
        local_ids = roster["competitor_id"].astype(str).tolist()
        as_of = str(request.get("prediction_as_of") or context.locked_at[:10])[:10]
        cutoff = f"{as_of}T00:00:00.000Z"
        snapshot = self._snapshot(context, cutoff)
        payload = {
            "workbook": str(snapshot),
            "cutoff_at_utc": cutoff,
            "scope_id": context.scope_id,
            "round_id": request["round_id"],
            "field_id": request["field_id"],
            "competitor_ids": local_ids,
            "target_context": dict(request["target_context"]),
            "ceiling": int(request.get("ceiling", 180)),
        }
        result = self._run("forecast" if forecast_only else "preview", payload)
        if (
            result.get("protocol") != LOCAL_V3_PROTOCOL
            or result.get("purpose") != "numeric_preview_only"
            or result.get("issued_mark") is not False
            or self._source_identity(result["readiness"]) != self.source_identity
        ):
            raise V3ClientError("local V3 response differs from the selected candidate")
        request_digest = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        ).hexdigest()
        if (
            result.get("request_digest") != request_digest
            or [row["competitor_id"] for row in result["rows"]] != local_ids
        ):
            raise V3ClientError("local V3 response does not match this exact request and roster")
        response_root = snapshot.parent / "previews"
        response_root.mkdir(exist_ok=True)
        operation = "forecast" if forecast_only else "preview"
        response_path = response_root / f"{operation}-{request_digest}.json"
        canonical = json.dumps(result, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        if response_path.exists() and response_path.read_text("utf-8") != canonical:
            raise V3ClientError("same local V3 request returned different numeric evidence")
        if not response_path.exists():
            response_path.write_text(canonical, encoding="utf-8")
        rows = []
        for index, item in enumerate(result["rows"]):
            row = {
                "name": str(roster.iloc[index]["competitor_name"]),
                "competitor_id": request["ordered_competitor_ids"][index],
                "predicted_time": float(item["predicted_time"]),
                "engine_version": item["engine_version"],
                "selected_engine": "v3",
                "returned_engine": "v3",
                "engine_mode": "rehearsal",
                "method_used": item["method_used"],
                "receipt_digest": result["source_digest"],
                "mark_origin": "unissued_linux_numeric_preview",
                "warnings": result["warnings"],
                "explanation": "Unpromoted Linux numeric preview: Formula + ML; no LLM council, approval, issue, or settlement authority.",
                "confidence": "CANDIDATE / PREVIEW ONLY",
                "std_dev": float(item["std_dev"]),
            }
            if not forecast_only:
                row["mark"] = int(item["proposed_mark"])
            rows.append(row)
        print("\n[V3 NUMERIC PREVIEW ONLY] Formula + trained ML. These proposed marks do not authorize issue.")
        return rows

    def _official_unavailable(self, *args, **kwargs):
        raise V3ClientError(
            "this local V3 profile supports numeric previews only; approval, issue, settlement, and next-round learning require the full authenticated V7 runtime"
        )

    approval_page = approval_detail = decide_approval = acknowledge_issue = settle_result = close_round = (
        close_scope
    ) = _official_unavailable


def build_local_v3_candidate(environ: Mapping[str, str] | None = None) -> LocalV3Candidate:
    runtime = os.environ if environ is None else environ
    names = (
        "STRATHEX_V3_LOCAL_PYTHON",
        "STRATHEX_V3_LOCAL_ML_BUNDLE",
        "STRATHEX_WORKBOOK",
        "STRATHEX_V3_LOCAL_SNAPSHOTS",
    )
    if any(not runtime.get(name) for name in names):
        raise V3RuntimeConfigurationError(
            "local V3 needs its separate Python, verified ML bundle, workbook, and snapshot directory"
        )
    try:
        return LocalV3Candidate(
            python=Path(runtime[names[0]]),
            ml_bundle=Path(runtime[names[1]]),
            workbook=Path(runtime[names[2]]),
            snapshot_root=Path(runtime[names[3]]),
        )
    except (OSError, TypeError, ValueError, subprocess.SubprocessError, V3ClientError) as error:
        raise V3RuntimeConfigurationError(f"local V3 candidate unavailable: {error}") from error
