"""Linux authority signature and lost-acknowledgment recovery regressions."""

from __future__ import annotations

import base64
import json
from dataclasses import replace

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

from woodchopping.engine_selection import PredictionExecutionContext
from woodchopping.strathmark_v3_client import V3ClientError, V3RecoveryRequired
from woodchopping.strathmark_v3_linux import (
    LINUX_CONTRACT_DIGEST,
    LINUX_PROTOCOL,
    LinuxV3Competition,
    digest,
    encoded,
    validate_local_trust,
)
from woodchopping.v3_authority_store import V3CommandStore


@pytest.fixture
def authority(tmp_path):
    private = ec.generate_private_key(ec.SECP256R1())
    public = base64.b64encode(
        private.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    ).decode()
    trust = {
        "key_id": "integrity-key:linux-" + digest({"public_key": public}),
        "key_class": "linux_installation",
        "provider": "linux_owner_private_p256_sha256",
        "public_key_der_b64": public,
    }
    client = object.__new__(LinuxV3Competition)
    client.trust, client.public_key = trust, validate_local_trust(trust)
    client.command_store = V3CommandStore(tmp_path / "commands.db")
    client.source_identity = "b" * 64
    client.competition_sources = {}
    context = PredictionExecutionContext(
        authority_store_id="synthetic",
        scope_id="tournament:synthetic",
        authority_revision=1,
        authority_digest="a" * 64,
        selected_engine="v3",
        mode="local",
        contract_identity=LINUX_CONTRACT_DIGEST,
        source_identity="b" * 64,
        selected_by_actor_id="synthetic-judge",
        selected_at_utc="2026-10-02T00:00:00.000Z",
        reason_code="synthetic_verification",
        locked=True,
        lock_boundary="first_authoritative_numeric_action",
        locked_at="2026-10-02T00:00:00.000Z",
        pre_field_signer_trust_json=json.dumps(trust),
    )

    def response(operation, envelope, value):
        identity = {
            "protocol": LINUX_PROTOCOL,
            "operation": operation,
            "request_digest": digest(envelope),
            "response_digest": digest(value),
        }
        body = {
            "schema_version": "strathmark-v3-integrity-body-v1",
            "kind": "linux_competition_response",
            "algorithm": "ecdsa-p256-sha256",
            "key_id": trust["key_id"],
            "created_at": "2026-10-02T01:00:00.000Z",
            "payload": identity,
        }
        return {
            **identity,
            "response": value,
            "manifest": {
                "schema_version": "strathmark-v3-signed-manifest-v1",
                "kind": body["kind"],
                "key_id": trust["key_id"],
                "body_json": encoded(body).decode(),
                "body_digest": digest(body),
                "signature_der_b64": base64.b64encode(private.sign(encoded(body), ec.ECDSA(hashes.SHA256()))).decode(),
            },
        }

    return client, context, response


def test_signed_response_rejects_changed_data_and_cross_command_replay(authority):
    client, context, sealed = authority
    envelope = {"command_id": "synthetic", "context": client._context(context), "payload": {"receipt": "synthetic"}}
    response = sealed("issue", envelope, {"issued": True})
    assert client._verify("issue", envelope, response) == {"issued": True}
    tampered = {**response, "response": {"issued": False}, "response_digest": digest({"issued": False})}
    with pytest.raises(V3ClientError, match="signature"):
        client._verify("issue", envelope, tampered)
    with pytest.raises(V3ClientError, match="exact command"):
        client._verify("settle", envelope, response)
    with pytest.raises(V3ClientError, match="exact command"):
        client._verify("issue", {**envelope, "command_id": "changed"}, response)
    with pytest.raises(V3ClientError, match="signer changed"):
        client._context(replace(context, pre_field_signer_trust_json=json.dumps({**client.trust, "key_id": "changed"})))
    with pytest.raises(V3ClientError, match="persistent installation"):
        validate_local_trust({**client.trust, "key_class": "development_ephemeral"})


def test_lost_response_retries_exact_command_and_caches_ack(authority, monkeypatch):
    client, context, sealed = authority
    sent = []

    def run(operation, envelope):
        sent.append(envelope)
        if len(sent) == 1:
            raise V3ClientError("response lost after producer commit")
        return sealed(operation, envelope, {"settled": True})

    monkeypatch.setattr(client, "_run", run)
    payload = {"receipt_id": "receipt:synthetic", "results": ["complete"]}
    with pytest.raises(V3RecoveryRequired) as error:
        client._command(context, "settle", payload, semantic="synthetic-result")
    key = error.value.command_key
    assert client.command_store.get(key).state == "recovery_required"
    with pytest.raises(V3RecoveryRequired):
        client._command(context, "settle", payload, semantic="synthetic-result")
    assert len(sent) == 1
    assert client.retry_recovery(key, context) == {"settled": True}
    assert sent[0] == sent[1]
    assert client._command(context, "settle", payload, semantic="synthetic-result") == {"settled": True}
    assert len(sent) == 2
    with pytest.raises(ValueError, match="different input"):
        client._command(context, "settle", {**payload, "results": ["changed"]}, semantic="synthetic-result")


def test_retained_competition_source_is_checked_before_cached_ack(authority, monkeypatch):
    client, context, sealed = authority
    monkeypatch.setattr(client, "_run", lambda operation, envelope: sealed(operation, envelope, {"settled": True}))
    payload = {"receipt_id": "receipt:synthetic", "results": [{"source_revision": 1}]}
    assert client.settle_result(context, payload) == {"settled": True}
    assert client.recover_result_request(context, payload["receipt_id"]) == payload
    client.source_identity = "c" * 64  # A newly installed model is a different new-scope authority.
    client.competition_sources = {context.scope_id: context.source_identity}
    assert client.settle_result(context, payload) == {"settled": True}
    with pytest.raises(V3ClientError, match="source identity"):
        client.settle_result(replace(context, source_identity=client.source_identity), payload)


def test_duplicate_names_keep_id_bound_outcomes_and_corrected_projections():
    import pandas as pd

    from woodchopping.data.excel_io import _display_names
    from woodchopping.ui.linux_results import collect_results, refresh_result_projections

    identifiers = pd.Series(["SYN001", "SYN002"])
    names = _display_names(pd.Series(["Same Name", "Same Name"]), identifiers)
    assert list(names) == ["Same Name [SYN001]", "Same Name [SYN002]"]
    field = {
        "handicap_results": [
            {"name": name, "local_competitor_id": identifier, "mark": 3}
            for name, identifier in zip(names, identifiers, strict=True)
        ]
    }
    answers = iter(["20", "DNS", "y", "y"])
    assert collect_results(field, input_fn=lambda _: next(answers))
    assert set(field["official_outcomes"]) == {"SYN001", "SYN002"}
    assert field["actual_results"] == {"Same Name [SYN001]": 20}
    field["official_outcomes"]["SYN001"]["raw_time_ms"] = 25000
    refresh_result_projections(field)
    assert field["actual_results"] == {"Same Name [SYN001]": 25}
    assert field["finish_order"] == {"Same Name [SYN001]": 1}
