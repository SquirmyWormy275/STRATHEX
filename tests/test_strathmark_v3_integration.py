from __future__ import annotations

import json
from dataclasses import replace

import pytest
import requests

from woodchopping.engine_selection import PredictionExecutionContext
from woodchopping.strathmark_v3_client import (
    FROZEN_V3_CONTRACT_DIGEST,
    FROZEN_V3_CONTRACT_VERSION,
    FROZEN_V3_SOURCE_COMMIT,
    V3ClientError,
    V3HttpClient,
    V3RecoveryRequired,
    get_v3_readiness,
)
from woodchopping.v3_authority_store import V3CommandStore


class _Response:
    def __init__(self, status_code: int, body: dict):
        self.status_code = status_code
        self._body = body

    def json(self):
        return self._body


class _Transport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def request(self, method, url, **kwargs):
        self.calls.append((method, url, kwargs))
        response = self.responses.pop(0)
        if isinstance(response, BaseException):
            raise response
        return response


def _context() -> PredictionExecutionContext:
    return PredictionExecutionContext(
        authority_store_id="store:test",
        scope_id="tournament:show",
        authority_revision=2,
        authority_digest="a" * 64,
        selected_engine="v3",
        mode="rehearsal",
        contract_identity=FROZEN_V3_CONTRACT_DIGEST,
        source_identity=FROZEN_V3_SOURCE_COMMIT,
        selected_by_actor_id="actor:judge-one",
        selected_at_utc="2026-08-27T16:00:00.000Z",
        reason_code="judge_selection",
        locked=True,
        lock_boundary="first_authoritative_numeric_action",
        locked_at="2026-08-27T16:00:00.000Z",
    )


def _client(tmp_path, responses):
    transport = _Transport(responses)
    client = V3HttpClient(
        base_url="http://127.0.0.1:8787",
        credential_provider=lambda: "smv3.test.secret",
        command_store=V3CommandStore(tmp_path / "v3-commands.db"),
        transport=transport,
    )
    return client, transport


def test_status_maps_candidate_to_rehearsal_and_never_leaks_secret(tmp_path):
    client, transport = _client(
        tmp_path,
        [
            _Response(
                200,
                {
                    "schema_version": "strathmark-v3-status-response-v1",
                    "service": "ready",
                    "v3_readiness": "candidate",
                    "production_authority": "v2",
                    "consumer_contract_digest": FROZEN_V3_CONTRACT_DIGEST,
                    "consumer_contract_version": FROZEN_V3_CONTRACT_VERSION,
                    "source_commit": FROZEN_V3_SOURCE_COMMIT,
                },
            )
        ],
    )

    readiness = client.readiness(_context())

    assert readiness.state == "rehearsal_ready"
    headers = transport.calls[0][2]["headers"]
    assert headers["Authorization"] == "Bearer smv3.test.secret"
    assert "smv3.test.secret" not in repr(readiness)


def test_module_readiness_supports_u6_preselection_without_locked_context(tmp_path):
    transport = _Transport(
        [
            _Response(
                200,
                {
                    "schema_version": "strathmark-v3-status-response-v1",
                    "service": "ready",
                    "v3_readiness": "candidate",
                    "production_authority": "v2",
                    "consumer_contract_digest": FROZEN_V3_CONTRACT_DIGEST,
                    "consumer_contract_version": FROZEN_V3_CONTRACT_VERSION,
                    "source_commit": FROZEN_V3_SOURCE_COMMIT,
                },
            )
        ]
    )
    environment = {
        "STRATHMARK_V3_BASE_URL": "http://127.0.0.1:8787",
        "STRATHMARK_V3_CREDENTIAL_ENV": "TEST_STRATHMARK_V3_SECRET",
        "TEST_STRATHMARK_V3_SECRET": "smv3.runtime.secret",
        "STRATHMARK_V3_CONTRACT_DIGEST": FROZEN_V3_CONTRACT_DIGEST,
        "STRATHMARK_V3_SOURCE_COMMIT": FROZEN_V3_SOURCE_COMMIT,
        "STRATHEX_V3_COMMAND_DB": str(tmp_path / "commands.db"),
        "STRATHMARK_V3_BUNDLE_ID": "bundle:strathex-current",
    }

    readiness = get_v3_readiness(environ=environment, transport=transport)

    assert readiness == {
        "status": "rehearsal_ready",
        "message": "Authenticated STRATHMARK V3 candidate is available for rehearsal.",
        "contract_identity": FROZEN_V3_CONTRACT_DIGEST,
        "source_identity": FROZEN_V3_SOURCE_COMMIT,
    }
    assert transport.calls[0][2]["headers"]["Authorization"] == ("Bearer smv3.runtime.secret")


@pytest.mark.parametrize(
    ("omitted_field", "expected_detail"),
    [
        ("consumer_contract_digest", "consumer_contract_evidence_missing"),
        ("consumer_contract_version", "consumer_contract_version_missing"),
        ("source_commit", "source_evidence_missing"),
    ],
)
def test_preselection_readiness_rejects_missing_service_identity_evidence(tmp_path, omitted_field, expected_detail):
    body = {
        "schema_version": "strathmark-v3-status-response-v1",
        "service": "ready",
        "v3_readiness": "candidate",
        "production_authority": "v2",
        "consumer_contract_digest": FROZEN_V3_CONTRACT_DIGEST,
        "consumer_contract_version": FROZEN_V3_CONTRACT_VERSION,
        "source_commit": FROZEN_V3_SOURCE_COMMIT,
    }
    del body[omitted_field]
    client, _ = _client(tmp_path, [_Response(200, body)])

    readiness = client.preselection_readiness()

    assert readiness.state == "ineligible"
    assert readiness.detail == expected_detail


def test_preselection_readiness_rejects_wrong_contract_version(tmp_path):
    client, _ = _client(
        tmp_path,
        [
            _Response(
                200,
                {
                    "schema_version": "strathmark-v3-status-response-v1",
                    "service": "ready",
                    "v3_readiness": "candidate",
                    "production_authority": "v2",
                    "consumer_contract_digest": FROZEN_V3_CONTRACT_DIGEST,
                    "consumer_contract_version": "strathmark.v3-consumer-contract.v999",
                    "source_commit": FROZEN_V3_SOURCE_COMMIT,
                },
            )
        ],
    )

    readiness = client.preselection_readiness()

    assert readiness.state == "ineligible"
    assert readiness.detail == "consumer_contract_version_mismatch"


@pytest.mark.parametrize(
    "environment",
    [
        {},
        {
            "STRATHMARK_V3_BASE_URL": "http://127.0.0.1:8787",
            "STRATHMARK_V3_CREDENTIAL_ENV": "MISSING_SECRET",
            "STRATHMARK_V3_CONTRACT_DIGEST": FROZEN_V3_CONTRACT_DIGEST,
            "STRATHMARK_V3_SOURCE_COMMIT": FROZEN_V3_SOURCE_COMMIT,
            "STRATHEX_V3_COMMAND_DB": "commands.db",
        },
        {
            "STRATHMARK_V3_BASE_URL": "http://127.0.0.1:8787",
            "STRATHMARK_V3_CREDENTIAL_ENV": "TEST_SECRET",
            "TEST_SECRET": "secret",
            "STRATHMARK_V3_CONTRACT_DIGEST": "0" * 64,
            "STRATHMARK_V3_SOURCE_COMMIT": FROZEN_V3_SOURCE_COMMIT,
            "STRATHEX_V3_COMMAND_DB": "commands.db",
        },
    ],
)
def test_module_readiness_fails_closed_for_absent_or_untrusted_runtime_config(
    environment,
):
    readiness = get_v3_readiness(environ=environment, transport=_Transport([]))

    assert readiness["status"] == "ineligible"
    assert "contract_identity" not in readiness
    assert "source_identity" not in readiness


def test_module_readiness_does_not_accept_a_raw_credential_setting(tmp_path):
    environment = {
        "STRATHMARK_V3_BASE_URL": "http://127.0.0.1:8787",
        "STRATHMARK_V3_CREDENTIAL": "raw-secrets-are-forbidden",
        "STRATHMARK_V3_CONTRACT_DIGEST": FROZEN_V3_CONTRACT_DIGEST,
        "STRATHMARK_V3_SOURCE_COMMIT": FROZEN_V3_SOURCE_COMMIT,
        "STRATHEX_V3_COMMAND_DB": str(tmp_path / "commands.db"),
    }

    readiness = get_v3_readiness(environ=environment, transport=_Transport([]))

    assert readiness["status"] == "ineligible"
    assert "raw-secrets-are-forbidden" not in repr(readiness)


def test_wrong_pin_and_non_loopback_http_fail_before_transport(tmp_path):
    client, transport = _client(tmp_path, [])
    bad = replace(_context(), source_identity="deadbeef")
    with pytest.raises(V3ClientError, match="source pin"):
        client.readiness(bad)
    assert transport.calls == []

    with pytest.raises(ValueError, match="loopback"):
        V3HttpClient(
            base_url="http://example.com:8787",
            credential_provider=lambda: "secret",
            command_store=V3CommandStore(tmp_path / "other.db"),
        )


def test_ambiguous_timeout_is_durable_and_exact_retry_reuses_idempotency(tmp_path):
    client, transport = _client(
        tmp_path,
        [
            requests.Timeout("late"),
            _Response(
                200,
                {
                    "schema_version": "strathmark-v3-scope-close-response-v1",
                    "scope_id": "tournament:show",
                    "authority_sequence": 8,
                    "status": "recovered",
                },
            ),
        ],
    )
    payload = {
        "schema_version": "strathmark-v3-scope-close-request-v1",
        "scope_id": "tournament:show",
        "closed_at_utc": "2026-08-27T17:00:00.000Z",
        "deadline_ms": 1000,
    }

    with pytest.raises(V3RecoveryRequired) as caught:
        client.close_scope(_context(), payload)
    command_key = caught.value.command_key
    assert client.command_store.get(command_key).state == "recovery_required"

    response = client.retry_recovery(command_key, _context())
    assert response["status"] == "recovered"
    assert client.command_store.get(command_key).state == "acknowledged"
    assert transport.calls[0][2]["headers"]["Idempotency-Key"] == transport.calls[1][2]["headers"]["Idempotency-Key"]


def test_recovery_survives_client_restart_with_reconstructed_authority(tmp_path):
    database = tmp_path / "v3-commands.db"
    first_transport = _Transport([requests.ConnectionError("uncertain")])
    first = V3HttpClient(
        base_url="http://localhost:8787",
        credential_provider=lambda: "first-credential",
        command_store=V3CommandStore(database),
        transport=first_transport,
    )
    payload = {
        "schema_version": "strathmark-v3-scope-close-request-v1",
        "scope_id": "tournament:show",
        "closed_at_utc": "2026-08-27T17:00:00.000Z",
        "deadline_ms": 1000,
    }
    with pytest.raises(V3RecoveryRequired) as caught:
        first.close_scope(_context(), payload)

    second_transport = _Transport(
        [
            _Response(
                200,
                {
                    "schema_version": "strathmark-v3-scope-close-response-v1",
                    "scope_id": "tournament:show",
                    "authority_sequence": 9,
                    "status": "recovered",
                },
            )
        ]
    )
    second = V3HttpClient(
        base_url="http://localhost:8787",
        credential_provider=lambda: "rotated-credential",
        command_store=V3CommandStore(database),
        transport=second_transport,
    )
    assert second.retry_recovery(caught.value.command_key, _context())["status"] == "recovered"
    assert second_transport.calls[0][2]["headers"]["Authorization"] == "Bearer rotated-credential"


def test_assemble_field_returns_selected_and_returned_v3_evidence(tmp_path):
    receipt = {
        "schema_version": "strathmark-v3-field-receipt-v1",
        "receipt_id": "receipt:field-1",
        "field_id": "field:heat-1",
        "ordered_competitor_ids": ["competitor:a", "competitor:b"],
        "engine_authority": {
            "scope_id": "tournament:show",
            "engine": "v3",
            "mode": "rehearsal",
            "selection_digest": "d" * 64,
            "consumer_contract_digest": FROZEN_V3_CONTRACT_DIGEST,
            "source_commit": FROZEN_V3_SOURCE_COMMIT,
        },
        "marks": [
            {"competitor_id": "competitor:a", "mark": 3},
            {"competitor_id": "competitor:b", "mark": 9},
        ],
        "warning_codes": [],
        "sections": [
            {
                "kind": "optimizer_frontier",
                "payload_type": "inline",
                "payload": {
                    "canonical_json": json.dumps(
                        {
                            "expected_times_ms": [
                                ["competitor:a", 30000],
                                ["competitor:b", 36000],
                            ]
                        },
                        separators=(",", ":"),
                    ),
                    "digest": "b" * 64,
                    "schema_version": "strathmark-v3-inline-payload-v1",
                },
                "schema_version": "strathmark-v3-receipt-section-v1",
            }
        ],
    }
    client, _ = _client(
        tmp_path,
        [
            _Response(
                200,
                {
                    "schema_version": "strathmark-v3-field-assembly-response-v1",
                    "receipt_id": "receipt:field-1",
                    "receipt_digest": "c" * 64,
                    "disposition": "prepared",
                    "canonical_receipt_json": json.dumps(receipt),
                    "authority_sequence": 9,
                },
            )
        ],
    )

    result = client(
        execution_context=_context(),
        field_id="field:heat-1",
        upstream_field_revision=1,
        ordered_competitor_ids=["competitor:a", "competitor:b"],
        competitor_names={"competitor:a": "Alice", "competitor:b": "Bob"},
    )

    assert [(row["name"], row["mark"], row["predicted_time"]) for row in result] == [
        ("Alice", 3, 30.0),
        ("Bob", 9, 36.0),
    ]
    assert all(row["selected_engine"] == "v3" and row["returned_engine"] == "v3" for row in result)
    assert all(row["engine_version"] == "3.0.0" for row in result)


def test_assemble_field_rejects_receipt_without_returned_engine_authority(tmp_path):
    receipt = {
        "receipt_id": "receipt:field-1",
        "ordered_competitor_ids": ["competitor:a", "competitor:b"],
        "marks": [
            {"competitor_id": "competitor:a", "mark": 3},
            {"competitor_id": "competitor:b", "mark": 9},
        ],
        "sections": [
            {
                "kind": "optimizer_frontier",
                "payload_type": "inline",
                "payload": {
                    "canonical_json": json.dumps(
                        {
                            "expected_times_ms": [
                                ["competitor:a", 30000],
                                ["competitor:b", 36000],
                            ]
                        }
                    )
                },
            }
        ],
    }
    client, _ = _client(
        tmp_path,
        [
            _Response(
                200,
                {
                    "schema_version": "strathmark-v3-field-assembly-response-v1",
                    "receipt_id": "receipt:field-1",
                    "receipt_digest": "c" * 64,
                    "canonical_receipt_json": json.dumps(receipt),
                },
            )
        ],
    )

    with pytest.raises(V3ClientError, match="incomplete or malformed"):
        client(
            execution_context=_context(),
            field_id="field:heat-1",
            upstream_field_revision=1,
            ordered_competitor_ids=["competitor:a", "competitor:b"],
        )


def test_authoritative_field_prepares_exact_field_before_assembly(tmp_path):
    receipt = {
        "receipt_id": "receipt:field-1",
        "ordered_competitor_ids": ["competitor:a", "competitor:b"],
        "engine_authority": {
            "scope_id": "tournament:show",
            "engine": "v3",
            "mode": "rehearsal",
            "consumer_contract_digest": FROZEN_V3_CONTRACT_DIGEST,
            "source_commit": FROZEN_V3_SOURCE_COMMIT,
        },
        "marks": [
            {"competitor_id": "competitor:a", "mark": 3},
            {"competitor_id": "competitor:b", "mark": 9},
        ],
        "sections": [
            {
                "kind": "optimizer_frontier",
                "payload_type": "inline",
                "payload": {
                    "canonical_json": json.dumps(
                        {"expected_times_ms": [["competitor:a", 30_000], ["competitor:b", 36_000]]}
                    )
                },
            }
        ],
    }
    lifecycle = [
        _Response(200, {"schema_version": "strathmark-v3-snapshot-sync-response-v1"}),
        _Response(200, {"schema_version": "strathmark-v3-snapshot-sync-response-v1"}),
        _Response(200, {"schema_version": "strathmark-v3-scope-open-response-v1"}),
        _Response(200, {"schema_version": "strathmark-v3-snapshot-sync-response-v1"}),
        _Response(200, {"schema_version": "strathmark-v3-round-freeze-response-v1"}),
        _Response(202, {"schema_version": "strathmark-v3-card-preparation-response-v1"}),
        _Response(202, {"schema_version": "strathmark-v3-card-preparation-response-v1"}),
        _Response(
            200,
            {
                "schema_version": "strathmark-v3-field-assembly-response-v1",
                "receipt_id": "receipt:field-1",
                "receipt_digest": "c" * 64,
                "canonical_receipt_json": json.dumps(receipt),
            },
        ),
    ]
    client, transport = _client(tmp_path, lifecycle)

    result = client(
        execution_context=_context(),
        tournament_id="tournament:show",
        round_id="round:heats",
        field_id="field:heat-1",
        upstream_field_revision=1,
        ordered_competitor_ids=["competitor:a", "competitor:b"],
        competitor_names={"competitor:a": "Alice", "competitor:b": "Bob"},
        stand_ids=["stand:one", "stand:two"],
        target_context={
            "schema_version": "strathmark-v3-target-context-v1",
            "event_code": "underhand",
            "size_mm": 325,
            "material_code": "pine",
            "taxonomy_version": "strathex:v1",
            "conversion_version": "strathex:v1",
            "properties": [],
        },
        historical_cutoff_key="history:before-show",
        requested_at_utc="2026-08-27T17:00:00.000Z",
        hard_deadline_at="2026-08-27T17:02:00.000Z",
    )

    assert [row["mark"] for row in result] == [3, 9]
    paths = [url.split("8787", 1)[1] for _, url, _ in transport.calls]
    assert paths == [
        "/v3/snapshots/synchronize",
        "/v3/snapshots/synchronize",
        "/v3/scopes/open",
        "/v3/snapshots/synchronize",
        "/v3/rounds/freeze",
        "/v3/cards/prepare",
        "/v3/cards/prepare",
        "/v3/fields/assemble",
    ]
    field_snapshot = transport.calls[3][2]["json"]
    assert field_snapshot["snapshot"]["stand_ids"] == ["stand:one", "stand:two"]


def test_pre_field_forecast_returns_signed_no_mark_seeding_projection(tmp_path):
    receipt = {
        "schema_version": "strathmark-v3-pre-field-forecast-receipt-v1",
        "purpose": "pre_field_seeding_only",
        "issued_mark": False,
        "snapshot": {
            "tournament_id": "tournament:show",
            "round_id": "round:heats",
            "ordered_competitor_ids": ["competitor:a", "competitor:b"],
            "engine_authority": {
                "scope_id": "tournament:show",
                "engine": "v3",
                "mode": "rehearsal",
                "selection_digest": "d" * 64,
                "consumer_contract_digest": FROZEN_V3_CONTRACT_DIGEST,
                "source_commit": FROZEN_V3_SOURCE_COMMIT,
            },
        },
        "forecasts": [
            {
                "competitor_id": "competitor:a",
                "p50_seed_time_ms": 30_000,
                "basis_kind": "capability_pool",
                "forecast_digest": "a" * 64,
            },
            {
                "competitor_id": "competitor:b",
                "p50_seed_time_ms": 36_000,
                "basis_kind": "zero_history_formula_prior",
                "forecast_digest": "b" * 64,
            },
        ],
        "receipt_digest": "c" * 64,
    }
    client, transport = _client(
        tmp_path,
        [
            _Response(
                200,
                {
                    "schema_version": "strathmark-v3-pre-field-forecast-response-v1",
                    "forecast_set_id": "forecast_set:one",
                    "receipt_digest": "c" * 64,
                    "disposition": "forecasted",
                    "purpose": "pre_field_seeding_only",
                    "issued_mark": False,
                    "canonical_receipt_json": json.dumps(receipt),
                    "authority_sequence": 10,
                },
            )
        ],
    )

    result = client.pre_field_forecast(
        _context(),
        tournament_id="tournament:show",
        round_id="round:heats",
        forecast_set_revision=1,
        ordered_competitor_ids=["competitor:a", "competitor:b"],
        competitor_names={"competitor:a": "Alice", "competitor:b": "Bob"},
        target_context={
            "schema_version": "strathmark-v3-target-context-v1",
            "event_code": "underhand",
            "size_mm": 325,
            "material_code": "pine",
            "taxonomy_version": "taxonomy:v1",
            "conversion_version": "conversion:v1",
            "properties": [],
        },
        hard_deadline_at="2026-08-27T17:10:00.000Z",
        requested_at_utc="2026-08-27T17:00:00.000Z",
    )

    assert [(row["name"], row["predicted_time"]) for row in result] == [
        ("Alice", 30.0),
        ("Bob", 36.0),
    ]
    assert all("mark" not in row for row in result)
    assert all(row["returned_engine"] == "v3" for row in result)
    sent = transport.calls[0][2]["json"]
    assert "field_id" not in sent
    assert "competitor_names" not in sent


def test_pre_field_forecast_rejects_mark_bearing_or_mismatched_receipt(tmp_path):
    receipt = {
        "purpose": "pre_field_seeding_only",
        "issued_mark": False,
        "snapshot": {
            "tournament_id": "tournament:other",
            "round_id": "round:heats",
            "ordered_competitor_ids": ["competitor:a"],
            "engine_authority": {},
        },
        "forecasts": [{"competitor_id": "competitor:a", "p50_seed_time_ms": 30_000, "mark": 3}],
        "receipt_digest": "c" * 64,
    }
    client, _ = _client(
        tmp_path,
        [
            _Response(
                200,
                {
                    "schema_version": "strathmark-v3-pre-field-forecast-response-v1",
                    "forecast_set_id": "forecast_set:one",
                    "receipt_digest": "c" * 64,
                    "disposition": "forecasted",
                    "purpose": "pre_field_seeding_only",
                    "issued_mark": False,
                    "canonical_receipt_json": json.dumps(receipt),
                    "authority_sequence": 10,
                },
            )
        ],
    )

    with pytest.raises(V3ClientError, match="incomplete or malformed"):
        client.pre_field_forecast(
            _context(),
            tournament_id="tournament:show",
            round_id="round:heats",
            forecast_set_revision=1,
            ordered_competitor_ids=["competitor:a"],
            target_context={},
            hard_deadline_at="2026-08-27T17:10:00.000Z",
            requested_at_utc="2026-08-27T17:00:00.000Z",
        )


def test_forecast_seeding_prepares_bound_scope_and_round_before_forecast(tmp_path):
    receipt = {
        "purpose": "pre_field_seeding_only",
        "issued_mark": False,
        "snapshot": {
            "tournament_id": "tournament:show",
            "round_id": "round:heats",
            "ordered_competitor_ids": ["competitor:a"],
            "engine_authority": {
                "scope_id": "tournament:show",
                "engine": "v3",
                "mode": "rehearsal",
                "consumer_contract_digest": FROZEN_V3_CONTRACT_DIGEST,
                "source_commit": FROZEN_V3_SOURCE_COMMIT,
            },
        },
        "forecasts": [
            {
                "competitor_id": "competitor:a",
                "p50_seed_time_ms": 30_000,
                "basis_kind": "capability_pool",
                "forecast_digest": "a" * 64,
            }
        ],
        "receipt_digest": "c" * 64,
    }
    client, transport = _client(
        tmp_path,
        [
            _Response(200, {"schema_version": "strathmark-v3-snapshot-sync-response-v1"}),
            _Response(200, {"schema_version": "strathmark-v3-snapshot-sync-response-v1"}),
            _Response(200, {"schema_version": "strathmark-v3-scope-open-response-v1"}),
            _Response(200, {"schema_version": "strathmark-v3-round-freeze-response-v1"}),
            _Response(
                200,
                {
                    "schema_version": "strathmark-v3-pre-field-forecast-response-v1",
                    "forecast_set_id": "forecast_set:one",
                    "receipt_digest": "c" * 64,
                    "purpose": "pre_field_seeding_only",
                    "issued_mark": False,
                    "canonical_receipt_json": json.dumps(receipt),
                },
            ),
        ],
    )

    result = client.forecast_seeding(
        execution_context=_context(),
        tournament_id="tournament:show",
        round_id="round:heats",
        forecast_set_revision=1,
        ordered_competitor_ids=["competitor:a"],
        competitor_names={"competitor:a": "Alice"},
        target_context={"schema_version": "test"},
        historical_cutoff_key="history:before-show",
        requested_at_utc="2026-08-27T17:00:00.000Z",
        hard_deadline_at="2026-08-27T17:02:00.000Z",
    )

    assert result[0]["name"] == "Alice"
    paths = [url.split("8787", 1)[1] for _, url, _ in transport.calls]
    assert paths == [
        "/v3/snapshots/synchronize",
        "/v3/snapshots/synchronize",
        "/v3/scopes/open",
        "/v3/rounds/freeze",
        "/v3/forecasts/pre-field",
    ]
    tournament_snapshot = transport.calls[0][2]["json"]
    assert tournament_snapshot["snapshot"] == {
        "bundle_id": "bundle:strathex-current",
        "historical_cutoff_key": "history:before-show",
    }
    assert tournament_snapshot["engine_selection"]["selected_by_actor_id"] == "actor:judge-one"
    assert "competitor_names" not in json.dumps([call[2]["json"] for call in transport.calls])


def test_acknowledged_lifecycle_command_replays_without_second_http_call(tmp_path):
    body = {
        "schema_version": "strathmark-v3-scope-open-response-v1",
        "scope_id": "tournament:show",
        "selection_digest": "a" * 64,
        "authority_sequence": 1,
        "status": "opened",
    }
    client, transport = _client(tmp_path, [_Response(200, body)])
    payload = {
        "schema_version": "strathmark-v3-scope-open-request-v1",
        "scope_id": "tournament:show",
        "bundle_id": "bundle:current",
        "historical_cutoff_key": "history:before-show",
        "root_round_ids": ["round:heats"],
        "engine_selection": {},
        "opened_at_utc": "2026-08-27T16:00:00.000Z",
        "deadline_ms": 1000,
    }

    assert client.open_scope(_context(), payload) == body
    assert client.open_scope(_context(), payload) == body
    assert len(transport.calls) == 1

    changed = dict(payload, opened_at_utc="2026-08-27T16:00:01.000Z")
    with pytest.raises(ValueError, match="already bound to different input"):
        client.open_scope(_context(), changed)
    assert len(transport.calls) == 1


def test_credential_is_not_persisted_in_durable_command_ledger(tmp_path):
    client, _ = _client(
        tmp_path,
        [
            _Response(
                200,
                {
                    "schema_version": "strathmark-v3-round-close-response-v1",
                    "round_id": "round:heats",
                    "closure_id": "round_closure:one",
                    "authority_sequence": 2,
                    "status": "closed",
                },
            )
        ],
    )
    client.close_round(
        _context(),
        {
            "schema_version": "strathmark-v3-round-close-request-v1",
            "round_id": "round:heats",
            "closed_at_utc": "2026-08-27T16:30:00.000Z",
            "deadline_ms": 1000,
        },
    )

    assert b"smv3.test.secret" not in (tmp_path / "v3-commands.db").read_bytes()


def test_definitive_rejection_is_not_retried_or_fallen_back(tmp_path):
    client, transport = _client(
        tmp_path,
        [
            _Response(
                409,
                {
                    "schema_version": "strathmark-v3-error-v1",
                    "code": "authority_conflict",
                    "message": "conflict",
                },
            )
        ],
    )
    payload = {
        "schema_version": "strathmark-v3-round-close-request-v1",
        "round_id": "round:heats",
        "closed_at_utc": "2026-08-27T16:30:00.000Z",
        "deadline_ms": 1000,
    }

    with pytest.raises(V3ClientError, match="authority_conflict"):
        client.close_round(_context(), payload)
    with pytest.raises(V3ClientError, match="previously rejected"):
        client.close_round(_context(), payload)
    assert len(transport.calls) == 1
