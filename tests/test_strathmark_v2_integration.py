"""Contract tests for STRATHEX's STRATHMARK v2 transports."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import date
from types import SimpleNamespace

import pandas as pd
import pytest

import woodchopping.strathmark_adapter as adapter

PREDICTION_AS_OF = date(2026, 8, 18)


def _history_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "competitor_id": ["C001", "C001", "C002", "C002"],
            "competitor_name": ["Alice Axe", "Alice Axe", "Bob Block", "Bob Block"],
            "event": ["SB", "SB", "SB", "SB"],
            "raw_time": [30.0, 31.0, 40.0, 39.0],
            "species": ["S01", "S01", "S01", "S01"],
            "size_mm": [300.0, 300.0, 300.0, 300.0],
            "quality": [5, 5, 5, 5],
            "date": pd.to_datetime(["2025-01-01", "2025-02-01", "2025-01-01", "2025-02-01"]),
        }
    )


def _mark_result(name: str = "Alice Axe", competitor_id: str = "C001") -> SimpleNamespace:
    return SimpleNamespace(
        name=name,
        competitor_id=competitor_id,
        mark=3,
        predicted_time=31.25,
        method_used="baseline",
        confidence="HIGH",
        explanation="STRATHMARK v2 hierarchical prior",
        std_dev=2.5,
        interval=SimpleNamespace(
            lower=27.0,
            upper=36.0,
            nominal_coverage=0.9,
            calibration_state="calibrated",
            scope="population",
        ),
        engine_version="2.0.0",
        model_version="prediction-v2-core-20260207",
        calibration_version="prediction-v2-calibration-2025h1",
        evidence_cutoff=PREDICTION_AS_OF,
        optimizer="posterior_crn_v2",
        warnings=["one undated result excluded"],
        prediction_id="pred-001",
        ledger_recorded=False,
        degraded=False,
        optimizer_metadata={"samples": 2048},
        ledger_status=None,
        provenance={"authority": "prediction_v2"},
        ignored_factors=["wood_quality", "tournament_results"],
    )


def _http_mark_payload() -> dict:
    result = _mark_result()
    return {
        "name": result.name,
        "competitor_id": result.competitor_id,
        "mark": result.mark,
        "predicted_time": result.predicted_time,
        "method_used": result.method_used,
        "confidence": result.confidence,
        "explanation": result.explanation,
        "std_dev": result.std_dev,
        "interval": vars(result.interval),
        "engine_version": result.engine_version,
        "model_version": result.model_version,
        "calibration_version": result.calibration_version,
        "evidence_cutoff": result.evidence_cutoff.isoformat(),
        "optimizer": result.optimizer,
        "warnings": result.warnings,
        "prediction_id": result.prediction_id,
        "ledger_recorded": result.ledger_recorded,
        "degraded": result.degraded,
        "optimizer_metadata": result.optimizer_metadata,
        "ledger_status": result.ledger_status,
        "provenance": result.provenance,
        "ignored_factors": result.ignored_factors,
    }


def _openapi_document(version: str = "2.0.0") -> dict:
    return {
        "info": {"version": version},
        "paths": {
            "/calculate": {
                "post": {
                    "requestBody": {
                        "content": {
                            "application/json": {"schema": {"$ref": "#/components/schemas/LegacyCalculateRequest"}}
                        }
                    },
                    "responses": {
                        "200": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {"$ref": "#/components/schemas/MarkResultResponse"},
                                    }
                                }
                            }
                        }
                    },
                }
            }
        },
        "components": {
            "schemas": {
                "LegacyCalculateRequest": {},
                "MarkResultResponse": {},
            }
        },
    }


def test_build_records_preserves_stable_identity_and_retires_tournament_weighting():
    records = adapter.build_competitor_records(
        ["Alice Axe"],
        _history_df(),
        tournament_results={"alice axe": 28.25},
        gender_map={"Alice Axe": "F"},
        competitor_id_map={"Alice Axe": "C001"},
    )

    record = records[0]
    assert record.competitor_id == "C001"
    assert record.gender == "F"
    assert record.tournament_time is None
    assert record.num_tournament_rounds == 1
    assert len(record.history) == 2


def test_roster_identity_wins_over_conflicting_history_identity():
    roster = pd.DataFrame(
        {
            "competitor_name": ["Alice Axe"],
            "competitor_id": ["C001"],
        }
    )
    history = _history_df().copy()
    history.loc[history["competitor_name"] == "Alice Axe", "competitor_id"] = "STALE-ID"

    identity_map = adapter.build_competitor_id_map(roster, history)

    assert identity_map["Alice Axe"] == "C001"
    assert identity_map["Bob Block"] == "C002"


def test_direct_transport_gives_v2_ownership_and_surfaces_audit_metadata(monkeypatch):
    calls = []

    class FakeCalculator:
        def calculate(self, **kwargs):
            calls.append(kwargs)
            return [_mark_result()]

    monkeypatch.setattr(adapter, "HandicapCalculator", FakeCalculator)

    records = adapter.build_competitor_records(
        ["Alice Axe"],
        _history_df(),
        competitor_id_map={"Alice Axe": "C001"},
    )
    output = adapter.calculate_handicap_results(
        records,
        adapter.build_wood_profile("S01", 300, 5),
        "SB",
        _history_df(),
        tournament_results={"Alice Axe": 28.25},
        prediction_as_of=PREDICTION_AS_OF,
        transport="python",
    )

    assert len(calls) == 1
    assert calls[0]["context"].prediction_as_of == PREDICTION_AS_OF
    assert "manual_overrides" not in calls[0]
    assert "tournament_results" not in calls[0]

    result = output[0]
    assert result["competitor_id"] == "C001"
    assert result["method_used"] == "V2 Core"
    assert result["engine_version"] == "2.0.0"
    assert result["optimizer"] == "posterior_crn_v2"
    assert result["prediction_interval"] == {
        "lower": 27.0,
        "upper": 36.0,
        "nominal_coverage": 0.9,
        "calibration_state": "calibrated",
        "scope": "population",
    }
    assert result["provenance"] == {"authority": "prediction_v2"}
    assert result["warnings"] == ["one undated result excluded"]
    assert result["ignored_factors"] == ["wood_quality", "tournament_results"]
    assert result["degraded"] is False
    assert result["transport"] == "python"


def test_http_transport_sends_one_stateless_field_request_with_identity_and_cutoff(monkeypatch):
    calls = []

    class FakeResponse:
        def __init__(self, payload, status_code=200):
            self._payload = payload
            self.status_code = status_code

        def raise_for_status(self):
            return None

        def json(self):
            return self._payload

    def fake_get(url, timeout, allow_redirects, stream):
        assert allow_redirects is False
        assert stream is True
        calls.append(("GET", url, None, timeout))
        return FakeResponse(_openapi_document())

    def fake_post(url, json, timeout, allow_redirects, stream):
        assert allow_redirects is False
        assert stream is True
        calls.append(("POST", url, json, timeout))
        return FakeResponse([_http_mark_payload()])

    monkeypatch.setattr(adapter.requests, "get", fake_get)
    monkeypatch.setattr(adapter.requests, "post", fake_post)

    records = adapter.build_competitor_records(
        ["Alice Axe"],
        _history_df(),
        competitor_id_map={"Alice Axe": "C001"},
    )
    output = adapter.calculate_handicap_results(
        records,
        adapter.build_wood_profile("S01", 300, 5),
        "SB",
        _history_df(),
        prediction_as_of=PREDICTION_AS_OF,
        transport="http",
        api_url="http://127.0.0.1:8000",
    )

    assert [call[0] for call in calls] == ["GET", "POST"]
    assert calls[0][1] == "http://127.0.0.1:8000/openapi.json"
    request_payload = calls[1][2]
    assert request_payload["prediction_as_of"] == "2026-08-18"
    assert request_payload["competitors"][0]["competitor_id"] == "C001"
    assert request_payload["competitors"][0]["history"][0]["result_date"] == "2025-01-01"
    assert "manual_overrides" not in request_payload
    assert "tournament_results" not in request_payload
    assert output[0]["engine_version"] == "2.0.0"
    assert output[0]["transport"] == "http"


def test_http_transport_rejects_version_mismatch_without_calculating(monkeypatch):
    class FakeResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return _openapi_document("1.9.0")

    monkeypatch.setattr(adapter.requests, "get", lambda url, timeout, allow_redirects, stream: FakeResponse())
    monkeypatch.setattr(adapter.requests, "post", lambda *args, **kwargs: pytest.fail("must fail before calculation"))

    records = adapter.build_competitor_records(["Alice Axe"], _history_df())
    with pytest.raises(RuntimeError, match="requires STRATHMARK API 2.0.0"):
        adapter.calculate_handicap_results(
            records,
            adapter.build_wood_profile("S01", 300, 5),
            "SB",
            _history_df(),
            prediction_as_of=PREDICTION_AS_OF,
            transport="http",
            api_url="http://localhost:8000",
        )


def test_direct_transport_rejects_result_engine_version_mismatch(monkeypatch):
    result = _mark_result()
    result.engine_version = "1.9.0"

    class FakeCalculator:
        def calculate(self, **kwargs):
            return [result]

    monkeypatch.setattr(adapter, "HandicapCalculator", FakeCalculator)
    records = adapter.build_competitor_records(
        ["Alice Axe"],
        _history_df(),
        competitor_id_map={"Alice Axe": "C001"},
    )

    with pytest.raises(RuntimeError, match="required v2 engine metadata"):
        adapter.calculate_handicap_results(
            records,
            adapter.build_wood_profile("S01", 300, 5),
            "SB",
            _history_df(),
            prediction_as_of=PREDICTION_AS_OF,
            transport="python",
        )


def test_http_transport_rejects_result_for_unrequested_identity(monkeypatch):
    class FakeResponse:
        status_code = 200

        def __init__(self, payload):
            self._payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self._payload

    payload = _http_mark_payload()
    payload["competitor_id"] = "C999"
    monkeypatch.setattr(
        adapter.requests,
        "get",
        lambda url, timeout, allow_redirects, stream: FakeResponse(_openapi_document()),
    )
    monkeypatch.setattr(
        adapter.requests,
        "post",
        lambda url, json, timeout, allow_redirects, stream: FakeResponse([payload]),
    )
    records = adapter.build_competitor_records(
        ["Alice Axe"],
        _history_df(),
        competitor_id_map={"Alice Axe": "C001"},
    )

    with pytest.raises(RuntimeError, match="unexpected competitor identity"):
        adapter.calculate_handicap_results(
            records,
            adapter.build_wood_profile("S01", 300, 5),
            "SB",
            _history_df(),
            prediction_as_of=PREDICTION_AS_OF,
            transport="http",
            api_url="http://localhost:8000",
        )


def test_result_identity_cannot_swap_the_trusted_roster_name(monkeypatch):
    result = _mark_result(name="Mallory Mask", competitor_id="C001")

    class FakeCalculator:
        def calculate(self, **kwargs):
            return [result]

    monkeypatch.setattr(adapter, "HandicapCalculator", FakeCalculator)
    records = adapter.build_competitor_records(
        ["Alice Axe"],
        _history_df(),
        competitor_id_map={"Alice Axe": "C001"},
    )

    with pytest.raises(RuntimeError, match="mismatched competitor name"):
        adapter.calculate_handicap_results(
            records,
            adapter.build_wood_profile("S01", 300, 5),
            "SB",
            _history_df(),
            prediction_as_of=PREDICTION_AS_OF,
            transport="python",
        )


def test_http_transport_rejects_plaintext_remote_urls():
    records = adapter.build_competitor_records(["Alice Axe"], _history_df())
    with pytest.raises(ValueError, match="HTTPS"):
        adapter.calculate_handicap_results(
            records,
            adapter.build_wood_profile("S01", 300, 5),
            "SB",
            _history_df(),
            prediction_as_of=PREDICTION_AS_OF,
            transport="http",
            api_url="http://demo.example.com",
        )


def test_http_transport_rejects_credential_bearing_urls():
    records = adapter.build_competitor_records(["Alice Axe"], _history_df())
    with pytest.raises(ValueError, match="must not contain credentials"):
        adapter.calculate_handicap_results(
            records,
            adapter.build_wood_profile("S01", 300, 5),
            "SB",
            _history_df(),
            prediction_as_of=PREDICTION_AS_OF,
            transport="http",
            api_url="https://user:password@demo.example.com",
        )


def test_http_transport_rejects_query_bearing_urls():
    records = adapter.build_competitor_records(["Alice Axe"], _history_df())
    with pytest.raises(ValueError, match="query string or fragment"):
        adapter.calculate_handicap_results(
            records,
            adapter.build_wood_profile("S01", 300, 5),
            "SB",
            _history_df(),
            prediction_as_of=PREDICTION_AS_OF,
            transport="http",
            api_url="https://demo.example.com?token=secret",
        )


def test_http_endpoint_label_never_echoes_credentials_or_secret_paths():
    assert adapter.describe_api_endpoint("https://demo.example.com:8443") == "https://demo.example.com:8443"
    with pytest.raises(ValueError, match="must not contain credentials"):
        adapter.describe_api_endpoint("https://user:secret@demo.example.com")
    with pytest.raises(ValueError, match="must not contain a path"):
        adapter.describe_api_endpoint("https://demo.example.com/private/token")


@pytest.mark.parametrize("timeout", ["nan", "inf", "0", "-1"])
def test_http_transport_rejects_non_finite_or_non_positive_timeout(timeout, monkeypatch):
    monkeypatch.setenv("STRATHMARK_API_TIMEOUT_SECONDS", timeout)
    monkeypatch.setattr(adapter.requests, "get", lambda *args, **kwargs: pytest.fail("must fail before I/O"))
    records = adapter.build_competitor_records(["Alice Axe"], _history_df())

    with pytest.raises(ValueError, match="finite and greater than zero"):
        adapter.calculate_handicap_results(
            records,
            adapter.build_wood_profile("S01", 300, 5),
            "SB",
            _history_df(),
            prediction_as_of=PREDICTION_AS_OF,
            transport="http",
            api_url="https://demo.example.com",
        )


def test_http_transport_rejects_redirect_before_sending_field(monkeypatch):
    class RedirectResponse:
        status_code = 307

        def raise_for_status(self):
            return None

        def json(self):
            return _openapi_document()

    monkeypatch.setattr(
        adapter.requests,
        "get",
        lambda url, timeout, allow_redirects, stream: RedirectResponse(),
    )
    monkeypatch.setattr(adapter.requests, "post", lambda *args, **kwargs: pytest.fail("must not POST"))
    records = adapter.build_competitor_records(["Alice Axe"], _history_df())

    with pytest.raises(RuntimeError, match="redirects are not allowed"):
        adapter.calculate_handicap_results(
            records,
            adapter.build_wood_profile("S01", 300, 5),
            "SB",
            _history_df(),
            prediction_as_of=PREDICTION_AS_OF,
            transport="http",
            api_url="https://demo.example.com",
        )


def test_http_transport_rejects_oversized_contract_response(monkeypatch):
    class OversizedResponse:
        status_code = 200
        headers = {"Content-Length": str(adapter._MAX_API_RESPONSE_BYTES + 1)}

        def raise_for_status(self):
            return None

        def json(self):
            pytest.fail("oversized body must not be decoded")

    monkeypatch.setattr(
        adapter.requests,
        "get",
        lambda url, timeout, allow_redirects, stream: OversizedResponse(),
    )
    monkeypatch.setattr(adapter.requests, "post", lambda *args, **kwargs: pytest.fail("must not POST"))
    records = adapter.build_competitor_records(["Alice Axe"], _history_df())

    with pytest.raises(RuntimeError, match="exceeded the response size limit"):
        adapter.calculate_handicap_results(
            records,
            adapter.build_wood_profile("S01", 300, 5),
            "SB",
            _history_df(),
            prediction_as_of=PREDICTION_AS_OF,
            transport="http",
            api_url="https://demo.example.com",
        )


def test_http_transport_rejects_same_version_server_without_calculate_contract(monkeypatch):
    class FakeResponse:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return {"info": {"version": "2.0.0"}}

    monkeypatch.setattr(
        adapter.requests,
        "get",
        lambda url, timeout, allow_redirects, stream: FakeResponse(),
    )
    monkeypatch.setattr(adapter.requests, "post", lambda *args, **kwargs: pytest.fail("must not POST"))
    records = adapter.build_competitor_records(["Alice Axe"], _history_df())

    with pytest.raises(RuntimeError, match="required v2 /calculate field contract"):
        adapter.calculate_handicap_results(
            records,
            adapter.build_wood_profile("S01", 300, 5),
            "SB",
            _history_df(),
            prediction_as_of=PREDICTION_AS_OF,
            transport="http",
            api_url="https://demo.example.com",
        )


def test_both_transports_share_the_api_field_size_and_wood_bounds(monkeypatch):
    records = adapter.build_competitor_records([f"Competitor {index}" for index in range(65)], pd.DataFrame())
    monkeypatch.setattr(adapter.requests, "get", lambda *args, **kwargs: pytest.fail("validation must precede I/O"))

    for transport in ("python", "http"):
        with pytest.raises(ValueError, match="limited to 64"):
            adapter.calculate_handicap_results(
                records,
                adapter.build_wood_profile("S01", 300, 5),
                "SB",
                pd.DataFrame(),
                prediction_as_of=PREDICTION_AS_OF,
                transport=transport,
                api_url="https://demo.example.com",
            )

    one_record = records[:1]
    for transport in ("python", "http"):
        with pytest.raises(ValueError, match="between 225 and 500"):
            adapter.calculate_handicap_results(
                one_record,
                adapter.build_wood_profile("S01", 200, 5),
                "SB",
                pd.DataFrame(),
                prediction_as_of=PREDICTION_AS_OF,
                transport=transport,
                api_url="https://demo.example.com",
            )


def test_both_transports_reject_empty_fields_before_engine_or_network(monkeypatch):
    monkeypatch.setattr(adapter.requests, "get", lambda *args, **kwargs: pytest.fail("validation must precede I/O"))

    class FailingCalculator:
        def calculate(self, **kwargs):
            pytest.fail("validation must precede engine calculation")

    monkeypatch.setattr(adapter, "HandicapCalculator", FailingCalculator)
    for transport in ("python", "http"):
        with pytest.raises(ValueError, match="at least one competitor"):
            adapter.calculate_handicap_results(
                [],
                adapter.build_wood_profile("S01", 300, 5),
                "SB",
                pd.DataFrame(),
                prediction_as_of=PREDICTION_AS_OF,
                transport=transport,
                api_url="https://demo.example.com",
            )


def test_result_missing_required_audit_metadata_is_rejected(monkeypatch):
    result = _mark_result()
    del result.provenance

    class FakeCalculator:
        def calculate(self, **kwargs):
            return [result]

    monkeypatch.setattr(adapter, "HandicapCalculator", FakeCalculator)
    records = adapter.build_competitor_records(
        ["Alice Axe"],
        _history_df(),
        competitor_id_map={"Alice Axe": "C001"},
    )

    with pytest.raises(RuntimeError, match="omitted required audit fields: provenance"):
        adapter.calculate_handicap_results(
            records,
            adapter.build_wood_profile("S01", 300, 5),
            "SB",
            _history_df(),
            prediction_as_of=PREDICTION_AS_OF,
            transport="python",
        )


def test_result_with_string_degraded_flag_is_rejected(monkeypatch):
    result = _mark_result()
    result.degraded = "false"

    class FakeCalculator:
        def calculate(self, **kwargs):
            return [result]

    monkeypatch.setattr(adapter, "HandicapCalculator", FakeCalculator)
    records = adapter.build_competitor_records(
        ["Alice Axe"],
        _history_df(),
        competitor_id_map={"Alice Axe": "C001"},
    )

    with pytest.raises(RuntimeError, match="invalid degraded metadata"):
        adapter.calculate_handicap_results(
            records,
            adapter.build_wood_profile("S01", 300, 5),
            "SB",
            _history_df(),
            prediction_as_of=PREDICTION_AS_OF,
            transport="python",
        )


def test_result_with_non_finite_interval_is_rejected(monkeypatch):
    result = _mark_result()
    result.interval.lower = float("nan")

    class FakeCalculator:
        def calculate(self, **kwargs):
            return [result]

    monkeypatch.setattr(adapter, "HandicapCalculator", FakeCalculator)
    records = adapter.build_competitor_records(
        ["Alice Axe"],
        _history_df(),
        competitor_id_map={"Alice Axe": "C001"},
    )

    with pytest.raises(RuntimeError, match="invalid prediction interval"):
        adapter.calculate_handicap_results(
            records,
            adapter.build_wood_profile("S01", 300, 5),
            "SB",
            _history_df(),
            prediction_as_of=PREDICTION_AS_OF,
            transport="python",
        )


def test_result_accepts_engine_maximum_legal_mark(monkeypatch):
    result = _mark_result()
    result.mark = adapter._sm_rules.MAX_MARK_SECONDS

    class FakeCalculator:
        def calculate(self, **kwargs):
            return [result]

    monkeypatch.setattr(adapter, "HandicapCalculator", FakeCalculator)
    records = adapter.build_competitor_records(
        ["Alice Axe"],
        _history_df(),
        competitor_id_map={"Alice Axe": "C001"},
    )

    output = adapter.calculate_handicap_results(
        records,
        adapter.build_wood_profile("S01", 300, 5),
        "SB",
        _history_df(),
        prediction_as_of=PREDICTION_AS_OF,
        transport="python",
    )

    assert output[0]["mark"] == adapter._sm_rules.MAX_MARK_SECONDS


def test_result_store_bootstrap_creates_one_recoverable_pre_v2_backup(tmp_path, monkeypatch):
    database = tmp_path / "results.db"
    with closing(sqlite3.connect(database)) as connection:
        connection.execute("CREATE TABLE legacy (value TEXT)")
        connection.execute("INSERT INTO legacy VALUES ('original')")
        connection.commit()
    sentinel = object()
    created_paths = []
    monkeypatch.setenv("STRATHMARK_DB_PATH", str(database))
    monkeypatch.setattr(adapter, "ResultStore", lambda db_path=None: created_paths.append(db_path) or sentinel)

    assert adapter.create_result_store() is sentinel
    backup = tmp_path / "results.db.pre-v2.bak"
    with closing(sqlite3.connect(backup)) as connection:
        assert connection.execute("SELECT value FROM legacy").fetchone() == ("original",)

    with closing(sqlite3.connect(database)) as connection:
        connection.execute("UPDATE legacy SET value = 'new-store'")
        connection.commit()
    assert adapter.create_result_store() is sentinel
    with closing(sqlite3.connect(backup)) as connection:
        assert connection.execute("SELECT value FROM legacy").fetchone() == ("original",)
    assert created_paths == [database.resolve(), database.resolve()]


def test_result_store_bootstrap_rejects_corrupt_existing_backup(tmp_path, monkeypatch):
    database = tmp_path / "results.db"
    with closing(sqlite3.connect(database)) as connection:
        connection.execute("CREATE TABLE legacy (value TEXT)")
        connection.commit()
    (tmp_path / "results.db.pre-v2.bak").write_bytes(b"partial")
    monkeypatch.setenv("STRATHMARK_DB_PATH", str(database))
    monkeypatch.setattr(adapter, "ResultStore", lambda db_path=None: pytest.fail("migration must not start"))

    with pytest.raises(RuntimeError, match="not a readable SQLite"):
        adapter.create_result_store()


def test_result_store_backup_includes_committed_wal_rows(tmp_path, monkeypatch):
    database = tmp_path / "results.db"
    connection = sqlite3.connect(database)
    try:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA wal_autocheckpoint=0")
        connection.execute("CREATE TABLE legacy (value TEXT)")
        connection.execute("INSERT INTO legacy VALUES ('committed-in-wal')")
        connection.commit()
        monkeypatch.setenv("STRATHMARK_DB_PATH", str(database))
        monkeypatch.setattr(adapter, "ResultStore", lambda db_path=None: object())

        adapter.create_result_store()

        with closing(sqlite3.connect(tmp_path / "results.db.pre-v2.bak")) as backup:
            assert backup.execute("SELECT value FROM legacy").fetchone() == ("committed-in-wal",)
    finally:
        connection.close()


@pytest.mark.strathmark
def test_real_python_and_http_transports_have_fixed_cutoff_parity(monkeypatch, request):
    from fastapi.testclient import TestClient
    from strathmark.api import app

    client = TestClient(app)
    request.addfinalizer(client.close)

    def app_get(url, timeout, allow_redirects, stream):
        del timeout, allow_redirects, stream
        return client.get(url.removeprefix("http://localhost:8000"))

    def app_post(url, json, timeout, allow_redirects, stream):
        del timeout, allow_redirects, stream
        return client.post(url.removeprefix("http://localhost:8000"), json=json)

    records = adapter.build_competitor_records(
        ["Alice Axe", "Bob Block"],
        _history_df(),
        competitor_id_map={"Alice Axe": "C001", "Bob Block": "C002"},
    )
    wood = adapter.build_wood_profile("S01", 300, 5)
    direct = adapter.calculate_handicap_results(
        records,
        wood,
        "SB",
        _history_df(),
        prediction_as_of=PREDICTION_AS_OF,
        transport="python",
    )

    monkeypatch.setattr(adapter.requests, "get", app_get)
    monkeypatch.setattr(adapter.requests, "post", app_post)
    remote = adapter.calculate_handicap_results(
        records,
        wood,
        "SB",
        _history_df(),
        prediction_as_of=PREDICTION_AS_OF,
        transport="http",
        api_url="http://localhost:8000",
    )

    assert [{key: value for key, value in row.items() if key != "transport"} for row in remote] == [
        {key: value for key, value in row.items() if key != "transport"} for row in direct
    ]
