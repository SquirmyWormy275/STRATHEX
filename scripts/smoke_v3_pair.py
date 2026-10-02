"""Exercise two installed distributions over loopback with synthetic V3 fixtures.

This is a development-key transport rehearsal, never production qualification.
The service checkout supplies only its reviewed test fixtures and public artifacts;
all application imports must resolve to the separately installed distributions.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
import venv
import zipfile
from dataclasses import replace
from datetime import datetime, timedelta
from importlib.metadata import distribution, version
from pathlib import Path


def write_json(path: Path, value: object) -> None:
    pending = path.with_suffix(path.suffix + ".pending")
    pending.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    pending.replace(path)


def require_installed(module: object, fixture_root: Path) -> str:
    path = Path(module.__file__).resolve()
    if "site-packages" not in path.parts or path.is_relative_to(fixture_root):
        raise RuntimeError(f"Application did not load from an installed distribution: {path}")
    if sys.version_info[:2] != (3, 13):
        raise RuntimeError("V3 rehearsal requires Python 3.13")
    return str(path)


def verify_wheel_installation(name: str, wheel: Path) -> str:
    installed = distribution(name)
    with zipfile.ZipFile(wheel) as archive:
        for entry in archive.namelist():
            if entry.endswith("/") or entry.endswith(".dist-info/RECORD"):
                continue
            if installed.locate_file(entry).read_bytes() != archive.read(entry):
                raise RuntimeError(f"Installed distribution differs from the supplied wheel: {entry}")
    return hashlib.sha256(wheel.read_bytes()).hexdigest()


def service_worker(args: argparse.Namespace) -> None:
    import strathmark
    import uvicorn

    installed = require_installed(strathmark, args.fixtures)
    wheel_digest = verify_wheel_installation("strathmark", args.service_wheel)
    from importlib.resources import files

    lock = files("strathmark.v3.contracts").joinpath("v3-release.lock").read_text("utf-8")
    for line in lock.splitlines():
        if line.strip() and not line.startswith("#"):
            name, expected = line.split("==")
            if version(name) != expected:
                raise RuntimeError(f"Installed service dependency differs from the release lock: {name}")
    # The immutable source fixtures construct synthetic cards and development keys.
    # Only their historical selection source is rebound to the reviewed installation.
    sys.path.insert(0, str(args.fixtures))
    from tests.v3.integration import test_v3_runtime_gateway as fixture

    original_bootstrap = fixture._bootstrap

    def bootstrap(*positional, **kwargs):
        kwargs["engine_selection"] = replace(kwargs["engine_selection"], source_commit=args.service_source)
        return original_bootstrap(*positional, **kwargs)

    fixture._bootstrap = bootstrap
    client, credential, store, field, _reactions, _jobs = fixture._runtime(
        args.state, service_source_commit=args.service_source
    )
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    config = uvicorn.Config(client.app, log_level="warning", access_log=False)
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
    thread.start()
    deadline = time.monotonic() + 30
    while not server.started:
        if not thread.is_alive() or time.monotonic() > deadline:
            raise RuntimeError("Synthetic loopback service did not start")
        time.sleep(0.05)
    write_json(
        args.state / "connection.json",
        {
            "base_url": f"http://127.0.0.1:{listener.getsockname()[1]}",
            "credential": credential,
            "installed_module": installed,
            "service_version": version("strathmark"),
            "scope_id": str(field.tournament_id),
            "round_id": str(field.round_id),
            "field_id": str(field.field_id),
            "field_revision": field.field_revision,
            "competitor_ids": [str(item.competitor_id) for item in field.ordered_assignments],
            "target_context": field.target_context.to_dict(),
            "hard_deadline_at": field.deadline_at,
            "selected_at": fixture.NOW,
        },
    )
    try:
        while not (args.state / "stop").exists():
            if not thread.is_alive():
                raise RuntimeError("Synthetic service stopped during rehearsal")
            time.sleep(0.1)
        store._events.verify()
        write_json(
            args.state / "service-result.json",
            {
                "event_chain_verified": True,
                "service_installed_module": installed,
                "service_version": version("strathmark"),
                "service_wheel_sha256": wheel_digest,
                "service_dependency_lock_sha256": hashlib.sha256(lock.encode()).hexdigest(),
            },
        )
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        listener.close()


def consumer_worker(args: argparse.Namespace) -> None:
    import requests

    import woodchopping
    from woodchopping.engine_selection import PredictionExecutionContext
    from woodchopping.strathmark_v3_client import (
        FROZEN_V3_CONTRACT_DIGEST,
        FROZEN_V3_SOURCE_COMMIT,
        V3HttpClient,
        V3RecoveryRequired,
    )
    from woodchopping.ui.prediction_context import AuthorityReference, PredictionAuthorityStore
    from woodchopping.v3_authority_store import V3CommandStore

    installed = require_installed(woodchopping, args.fixtures)
    wheel_digest = verify_wheel_installation("strathex", args.consumer_wheel)
    if args.service_source != FROZEN_V3_SOURCE_COMMIT:
        raise RuntimeError("Service source does not match the installed consumer pin")
    connection = json.loads((args.state / "connection.json").read_text("utf-8"))
    authority = PredictionAuthorityStore(args.state / "consumer-authority.sqlite3")

    def clock():
        return datetime.fromisoformat(connection["hard_deadline_at"].replace("Z", "+00:00")) - timedelta(seconds=30)

    def make_client(transport=None):
        return V3HttpClient(
            base_url=connection["base_url"],
            credential_provider=lambda: connection["credential"],
            command_store=V3CommandStore(args.state / "consumer-commands.sqlite3"),
            transport=transport,
            clock=clock,
        )

    client = make_client()
    if args.role == "recover":
        saved = json.loads((args.state / "recovery.json").read_text("utf-8"))
        receipt = authority.resolve(AuthorityReference.from_json(saved["reference"]))
        context = PredictionExecutionContext.from_receipt(receipt)
        recovered = client.retry_recovery(saved["command_key"], context)
        if client.retry_recovery(saved["command_key"], context) != recovered:
            raise RuntimeError("Acknowledged retry changed the settlement response")
        if recovered["status"] != "recovered":
            raise RuntimeError("Lost settlement response was not recovered from service authority")
        before = client.approval_page(context, tournament_id=context.scope_id, offset=0, limit=25)
        immutable = client.lookup_receipt(
            context,
            {
                "schema_version": "strathmark-v3-receipt-lookup-request-v1",
                "request_identity": "lookup:installed-synthetic",
                "receipt_id": saved["receipt_id"],
                "deadline_ms": 5_000,
            },
        )
        if immutable["receipt_digest"] != saved["receipt_digest"] or before["lifecycle_state"] != "all_issued":
            raise RuntimeError("Settlement altered the issued receipt")
        write_json(args.state / "consumer-recovered.json", {"process_restart": True, "exact_settlement_recovery": True})
        return

    readiness = client.preselection_readiness()
    if readiness.state != "rehearsal_ready" or readiness.source_commit != args.service_source:
        raise RuntimeError(f"Installed service failed consumer readiness: {readiness}")
    created = authority.create_scope(owner_kind="tournament", scope_id=connection["scope_id"])
    selected = authority.select_engine(
        created.reference,
        engine="v3",
        mode="rehearsal",
        actor="actor:manager",
        selected_at=connection["selected_at"],
        reason_code="runtime_contract_proof",
        contract_identity=FROZEN_V3_CONTRACT_DIGEST,
        source_identity=args.service_source,
        pre_field_signer_trust=json.loads(readiness.pre_field_signer_trust_json),
    )
    locked = authority.lock(
        selected.reference, boundary="first_authoritative_numeric_action", locked_at=connection["selected_at"]
    )
    context = PredictionExecutionContext.from_receipt(locked)
    forecasts = client.pre_field_forecast(
        context,
        tournament_id=context.scope_id,
        round_id=connection["round_id"],
        forecast_set_revision=1,
        ordered_competitor_ids=connection["competitor_ids"],
        target_context=connection["target_context"],
        hard_deadline_at=connection["hard_deadline_at"],
        requested_at_utc=connection["selected_at"],
        deadline_ms=10_000,
    )
    if len(forecasts) != len(connection["competitor_ids"]) or any("mark" in row for row in forecasts):
        raise RuntimeError("Pre-field seeding returned marks or an incomplete roster")
    projection = client(
        execution_context=context,
        field_id=connection["field_id"],
        upstream_field_revision=connection["field_revision"],
        ordered_competitor_ids=connection["competitor_ids"],
        deadline_ms=10_000,
    )
    if len(projection) != len(forecasts) or min(row["mark"] for row in projection) != 3:
        raise RuntimeError("Exact-field projection is incomplete or not rebased to Mark 3")
    page = client.approval_page(context, tournament_id=context.scope_id, offset=0, limit=25)
    row = next(item for item in page["rows"] if item["field_id"] == connection["field_id"])
    selection = {
        key: row[key]
        for key in ("field_id", "receipt_id", "receipt_revision", "upstream_field_revision", "row_digest", "call_order")
    }
    selection["receipt_digest"] = row["receipt_content_digest"]
    approval = {
        "schema_version": "strathmark-v3-approval-decision-request-v1",
        "tournament_id": context.scope_id,
        "snapshot_id": page["snapshot_id"],
        "action": "individual_accept",
        "selected": [selection],
        "excluded": [],
        "actor_metadata": {"station": "installed-synthetic-rehearsal"},
        "reason_code": "synthetic_sheet_reviewed",
        "superseded_receipt_id": None,
        "decided_at_utc": "2026-08-25T18:00:01.000Z",
        "deadline_ms": 10_000,
    }
    accepted = client.decide_approval(context, approval)
    if client.decide_approval(context, approval) != accepted:
        raise RuntimeError("Approval acknowledgment is not immutable")
    approved = client.approval_page(context, tournament_id=context.scope_id, offset=0, limit=25)
    if approved["rows"][0]["decision_state"] != "accepted":
        raise RuntimeError("Approval was conflated with official issue")
    issue = {
        "schema_version": "strathmark-v3-issue-acknowledgment-request-v1",
        "upstream_issue_id": "upstream_issue:installed-synthetic",
        "receipt_bindings": [{"receipt_id": row["receipt_id"], "receipt_digest": row["receipt_content_digest"]}],
        "issued_at_utc": "2026-08-25T18:00:02.000Z",
        "deadline_ms": 10_000,
    }
    issued = client.acknowledge_issue(context, issue)
    if client.acknowledge_issue(context, issue) != issued:
        raise RuntimeError("Issue acknowledgment is not immutable")

    class LoseResponse:
        """Discard one successful HTTP response after the service committed it."""

        def __init__(self):
            self.session = requests.Session()
            self.session.trust_env = False

        def request(self, method, url, **kwargs):
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            raise requests.ReadTimeout("synthetic response loss after service commit")

    settlement = {
        "schema_version": "strathmark-v3-settlement-request-v1",
        "issue_batch_id": issued["issue_batch_id"],
        "receipt_id": row["receipt_id"],
        "results": [
            {
                "competitor_id": competitor,
                "status": "completion",
                "raw_time_ms": 40_000 + index * 1_000,
                "penalty_ms": None,
                "source_revision": 1,
            }
            for index, competitor in enumerate(connection["competitor_ids"])
        ],
        "observed_at_utc": "2026-08-25T18:00:03.000Z",
        "deadline_ms": 10_000,
    }
    try:
        make_client(LoseResponse()).settle_result(context, settlement)
    except V3RecoveryRequired as error:
        write_json(
            args.state / "recovery.json",
            {
                "command_key": error.command_key,
                "reference": locked.reference.to_json(),
                "receipt_id": row["receipt_id"],
                "receipt_digest": row["receipt_content_digest"],
            },
        )
    else:
        raise RuntimeError("Lost response did not block the command pending deliberate recovery")
    write_json(
        args.state / "consumer-result.json",
        {
            "installed_module": installed,
            "consumer_version": version("strathex"),
            "consumer_v2_version": version("strathmark"),
            "consumer_wheel_sha256": wheel_digest,
            "service_source": args.service_source,
            "contract_digest": FROZEN_V3_CONTRACT_DIGEST,
            "mark_free_seeding": True,
            "exact_field": True,
            "approval_separate_from_issue": True,
            "immutable_approval_and_issue": True,
            "ambiguous_settlement_blocked": True,
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--service-checkout", type=Path)
    parser.add_argument("--service-source", required=True)
    parser.add_argument("--service-python", type=Path)
    parser.add_argument("--consumer-python", type=Path)
    parser.add_argument("--service-wheel", type=Path, required=True)
    parser.add_argument("--consumer-wheel", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--role", choices=("service", "consumer", "recover"))
    parser.add_argument("--fixtures", type=Path)
    parser.add_argument("--state", type=Path)
    args = parser.parse_args()
    if args.role:
        service_worker(args) if args.role == "service" else consumer_worker(args)
        return
    if not all((args.service_checkout, args.output)):
        parser.error("Rehearsal requires service checkout and output")
    if bool(args.service_python) != bool(args.consumer_python):
        parser.error("Supply both installed Python paths or allow creation of two fresh environments")
    checkout = args.service_checkout.resolve(strict=True)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=checkout, text=True).strip()
    status = subprocess.check_output(["git", "status", "--porcelain"], cwd=checkout, text=True).strip()
    if head != args.service_source or status:
        raise RuntimeError("Service fixture checkout must be clean at the exact reviewed source")
    with zipfile.ZipFile(args.service_wheel) as wheel:
        for entry in wheel.namelist():
            if entry.startswith("strathmark/") and entry.endswith(".py"):
                if (checkout / entry).read_bytes() != wheel.read(entry):
                    raise RuntimeError(f"Service wheel Python source differs from reviewed checkout: {entry}")
    archive = subprocess.check_output(["git", "archive", "--format=zip", head, "tests", "benchmarks"], cwd=checkout)
    script = str(Path(__file__).resolve())
    with tempfile.TemporaryDirectory(prefix="strath-installed-v3-pair-") as temporary:
        root = Path(temporary)
        fixtures, state = root / "fixtures", root / "state"
        fixtures.mkdir()
        state.mkdir(mode=0o700)
        with zipfile.ZipFile(io.BytesIO(archive)) as zipped:
            zipped.extractall(fixtures)
        env = {key: value for key, value in os.environ.items() if not key.startswith(("STRATHMARK_", "STRATHEX_"))}
        env.update(STRATHMARK_TEST_DB="1", PYTHONUTF8="1", STRATHMARK_DB_PATH=str(state / "isolated-v2.sqlite3"))
        for key, name in {
            "DB_PATH": "isolated-v3.sqlite3",
            "TEMP_PATH": "runtime",
            "BLOB_ROOT": "blobs",
            "BUNDLE_ROOT": "bundles",
            "ARCHIVE_ROOT": "archive",
            "BACKUP_ROOT": "backup",
            "RECOVERY_ROOT": "recovery-device",
            "INTEGRITY_KEY_ROOT": "development-keys",
        }.items():
            env[f"STRATHMARK_V3_{key}"] = str(state / name)
        if not args.service_python:
            if sys.version_info[:2] != (3, 13):
                raise RuntimeError("Creating V3 environments requires Python 3.13")
            for name in ("consumer", "service"):
                environment = root / f"{name}-environment"
                venv.EnvBuilder(with_pip=True).create(environment)
                python = environment / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
                setattr(args, f"{name}_python", python)
                install = [str(python), "-m", "pip", "install", "--disable-pip-version-check"]
                if name == "consumer":
                    install.append(f"{args.consumer_wheel.resolve()}[api-test]")
                else:
                    install.extend(
                        [
                            str(args.service_wheel.resolve()),
                            "-r",
                            str(checkout / "requirements/v3-release.lock"),
                            "pytest",
                        ]
                    )
                subprocess.run(install, cwd=root, env=env, check=True, timeout=300)
        common = [
            "-I",
            script,
            "--service-source",
            head,
            "--fixtures",
            str(fixtures),
            "--state",
            str(state),
            "--service-wheel",
            str(args.service_wheel.resolve(strict=True)),
            "--consumer-wheel",
            str(args.consumer_wheel.resolve(strict=True)),
        ]
        with (state / "service.log").open("w", encoding="utf-8") as log:
            service = subprocess.Popen(
                [str(args.service_python.absolute()), *common, "--role", "service"],
                cwd=fixtures,
                env=env,
                stdout=log,
                stderr=log,
            )
            try:
                deadline = time.monotonic() + 60
                while not (state / "connection.json").exists():
                    if service.poll() is not None or time.monotonic() > deadline:
                        raise RuntimeError("Service bootstrap failed: " + (state / "service.log").read_text("utf-8"))
                    time.sleep(0.1)
                for role in ("consumer", "recover"):
                    subprocess.run(
                        [str(args.consumer_python.absolute()), *common, "--role", role],
                        cwd=root,
                        env=env,
                        check=True,
                        timeout=90,
                    )
                (state / "stop").touch()
                service.wait(timeout=20)
                if service.returncode:
                    raise RuntimeError((state / "service.log").read_text("utf-8"))
                result = {
                    "schema_version": "strath-installed-v3-pair-rehearsal-v1",
                    "passed": True,
                    "authority_changed": False,
                    "evidence_tier": "synthetic_development_key",
                    "fixture_archive_sha256": hashlib.sha256(archive).hexdigest(),
                    "limitations": [
                        "Synthetic presealed assessor cards and test settlement reactions",
                        "No designated model, formula runtime, CNG, OS ACL, or capacity qualification",
                        "Consumer process restart; no service-machine restart or next-round forecast proof",
                    ],
                }
                for filename in ("consumer-result.json", "consumer-recovered.json", "service-result.json"):
                    result.update(json.loads((state / filename).read_text("utf-8")))
                args.output.parent.mkdir(parents=True, exist_ok=True)
                write_json(args.output, result)
                print(json.dumps(result, indent=2))
            finally:
                if service.poll() is None:
                    service.terminate()
                    try:
                        service.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        service.kill()
                        service.wait(timeout=10)


if __name__ == "__main__":
    main()
