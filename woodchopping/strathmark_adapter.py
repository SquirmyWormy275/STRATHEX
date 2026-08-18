# -*- coding: utf-8 -*-
"""
STRATHEX <-> STRATHMARK adapter.

This module is the single production boundary between STRATHEX's DataFrame-
based tournament application and STRATHMARK's typed prediction engine. It
translates records, delegates one v2 field calculation, preserves audit
metadata, and exposes small compatibility facades for persistence and simulation.

No tournament workflow or user-interface policy belongs here.
"""

from __future__ import annotations

import json
import logging
import math
import os
import sqlite3
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Mapping, Optional
from urllib.parse import urlparse

import pandas as pd
import requests
import strathmark.variance as _sm_variance
from strathmark import (
    CompetitorRecord,
    HandicapCalculator,
    HistoricalResult,
    PredictionContext,
    ResultStore,
    WoodProfile,
)
from strathmark.config import rules as _sm_rules
from strathmark.fairness import (
    get_ai_assessment_of_handicaps as _sm_assess_handicaps,
)
from strathmark.fairness import (
    get_championship_race_analysis as _sm_championship_analysis,
)
from strathmark.fairness import (
    simulate_and_assess_handicaps as _sm_simulate_and_assess,
)

from woodchopping.prediction_context import resolve_prediction_as_of

_log = logging.getLogger(__name__)
_STRATHMARK_API_VERSION = "2.0.0"
_DEFAULT_API_TIMEOUT_SECONDS = 10.0
_MAX_API_RESPONSE_BYTES = 4 * 1024 * 1024
MAX_STRATHMARK_FIELD_SIZE = 64
_MIN_TIME_SECONDS = 3.0
_MAX_TIME_SECONDS = 180.0
_MIN_DIAMETER_MM = 225.0
_MAX_DIAMETER_MM = 500.0
_REQUIRED_RESULT_FIELDS = {
    "name",
    "mark",
    "predicted_time",
    "method_used",
    "confidence",
    "explanation",
    "std_dev",
    "competitor_id",
    "interval",
    "engine_version",
    "model_version",
    "calibration_version",
    "evidence_cutoff",
    "optimizer",
    "warnings",
    "degraded",
    "optimizer_metadata",
    "provenance",
    "ignored_factors",
}


# ---------------------------------------------------------------------------
# Normalisation helpers
# ---------------------------------------------------------------------------


def _name_key(value: Any) -> str:
    """Return a stable, case-insensitive key for a competitor name."""
    if value is None or pd.isna(value):
        return ""
    return str(value).strip().casefold()


def _clean_gender(value: Any) -> Optional[str]:
    """Normalise roster gender values to STRATHMARK's ``M`` / ``F`` encoding."""
    if value is None or pd.isna(value):
        return None
    text = str(value).strip().upper()
    if text in {"M", "MALE", "MEN", "MAN"}:
        return "M"
    if text in {"F", "FEMALE", "WOMEN", "WOMAN"}:
        return "F"
    return None


def _clean_optional_text(value: Any) -> Optional[str]:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    return text or None


def prepare_results_for_strathmark(
    results_df: Optional[pd.DataFrame],
) -> pd.DataFrame:
    """Return a unique-column DataFrame safe for the pinned engine boundary.

    STRATHEX's loaded Results frame legitimately carries both ``competitor_id``
    and ``competitor_name``. STRATHMARK v2 treats stable identity and display
    name as separate values, so both columns are deliberately preserved.

    Only colliding alias families are rewritten. Frames that are already safe
    are returned unchanged so existing cache and caller identity semantics remain
    intact. Canonical values win; aliases fill only missing cells.
    """
    if results_df is None or not isinstance(results_df, pd.DataFrame):
        return pd.DataFrame()
    if results_df.empty:
        return results_df

    normalized_names = [str(column).strip().lower() for column in results_df.columns]
    alias_groups = {
        "competitor_name": (
            "competitor_name",
            "competitor name",
            "competitorname",
            "name",
        ),
        "event": ("event", "event_code", "eventcode"),
        "raw_time": (
            "raw_time",
            "actual_time",
            "actualtime",
            "time",
            "time (seconds)",
            "time(seconds)",
        ),
        "size_mm": (
            "size_mm",
            "diameter_mm",
            "diameter",
            "size",
            "size (mm)",
            "size(mm)",
        ),
        "species": (
            "species",
            "wood_species",
            "woodspecies",
            "species code",
            "speciescode",
        ),
        "result_date": (
            "result_date",
            "result date",
            "date",
            "date (optional)",
        ),
    }

    collisions: Dict[str, List[int]] = {}
    for target, aliases in alias_groups.items():
        positions = [position for alias in aliases for position, name in enumerate(normalized_names) if name == alias]
        if len(positions) > 1:
            collisions[target] = positions

    if not collisions and results_df.columns.is_unique:
        return results_df

    consumed_positions = {position for positions in collisions.values() for position in positions}
    output = pd.DataFrame(index=results_df.index)

    for position, column_name in enumerate(results_df.columns):
        if position in consumed_positions:
            continue
        normalized = str(column_name).strip().lower()
        if normalized not in output.columns:
            output[normalized] = results_df.iloc[:, position]

    for target, positions in collisions.items():
        combined = results_df.iloc[:, positions[0]].copy()
        for position in positions[1:]:
            candidate = results_df.iloc[:, position]
            missing = combined.isna()
            if combined.dtype == object:
                missing = missing | combined.astype(str).str.strip().eq("")
            combined = combined.where(~missing, candidate)
        output[target] = combined

    return output


def enrich_results_with_roster(
    results_df: Optional[pd.DataFrame],
    roster_df: Optional[pd.DataFrame],
) -> pd.DataFrame:
    """
    Fill historical-result gender values from the competitor roster.

    STRATHMARK's ML feature schema includes gender.  The Results sheet stores
    performance observations while the Competitor sheet stores gender, so the
    two sources must be joined before model training.  Existing valid result
    values are preserved and the input DataFrames are never mutated.
    """
    results = results_df.copy() if isinstance(results_df, pd.DataFrame) else pd.DataFrame()
    if results.empty or roster_df is None or roster_df.empty:
        return results

    roster = roster_df.copy()
    roster.columns = [str(col).strip() for col in roster.columns]
    roster.rename(
        columns={
            "Name": "competitor_name",
            "name": "competitor_name",
            "Competitor Name": "competitor_name",
            "Gender": "gender",
        },
        inplace=True,
    )

    if "competitor_name" not in results.columns or not {
        "competitor_name",
        "gender",
    }.issubset(roster.columns):
        return results

    gender_by_name: Dict[str, str] = {}
    for _, row in roster[["competitor_name", "gender"]].iterrows():
        key = _name_key(row.get("competitor_name"))
        gender = _clean_gender(row.get("gender"))
        if key and gender:
            gender_by_name[key] = gender

    if not gender_by_name:
        return results

    mapped = results["competitor_name"].map(lambda value: gender_by_name.get(_name_key(value)))
    if "gender" not in results.columns:
        results["gender"] = mapped
    else:
        existing = results["gender"].map(_clean_gender)
        results["gender"] = existing.where(existing.notna(), mapped)

    return results


def build_gender_map(
    competitor_df: Optional[pd.DataFrame],
    results_df: Optional[pd.DataFrame] = None,
) -> Dict[str, str]:
    """Build an exact-name -> gender map for current competitor records."""
    by_key: Dict[str, str] = {}
    display_name_by_key: Dict[str, str] = {}

    for frame in (competitor_df, results_df):
        if frame is None or frame.empty or "competitor_name" not in frame.columns:
            continue
        if "gender" not in frame.columns:
            continue

        for _, row in frame[["competitor_name", "gender"]].iterrows():
            name = _clean_optional_text(row.get("competitor_name"))
            gender = _clean_gender(row.get("gender"))
            key = _name_key(name)
            if key and gender:
                by_key[key] = gender
                display_name_by_key.setdefault(key, name or key)

    return {display_name_by_key[key]: value for key, value in by_key.items()}


def build_competitor_id_map(
    competitor_df: Optional[pd.DataFrame],
    results_df: Optional[pd.DataFrame] = None,
) -> Dict[str, str]:
    """Build a display-name -> stable competitor ID map for STRATHMARK v2."""
    by_key: Dict[str, str] = {}
    display_name_by_key: Dict[str, str] = {}

    for frame in (competitor_df, results_df):
        if frame is None or frame.empty:
            continue
        normalized = frame.copy()
        normalized.columns = [str(column).strip().lower() for column in normalized.columns]
        if not {"competitor_name", "competitor_id"}.issubset(normalized.columns):
            continue

        for _, row in normalized[["competitor_name", "competitor_id"]].iterrows():
            name = _clean_optional_text(row.get("competitor_name"))
            competitor_id = _clean_optional_text(row.get("competitor_id"))
            key = _name_key(name)
            if key and competitor_id:
                # The selected roster is authoritative. Historical rows only
                # fill an identity that the roster did not provide.
                by_key.setdefault(key, competitor_id)
                display_name_by_key.setdefault(key, name or key)

    return {display_name_by_key[key]: value for key, value in by_key.items()}


# ---------------------------------------------------------------------------
# Build STRATHMARK input objects
# ---------------------------------------------------------------------------


def build_competitor_records(
    competitor_names: List[str],
    results_df: pd.DataFrame,
    division_map: Optional[Dict[str, str]] = None,
    tournament_results: Optional[Dict[str, float]] = None,
    gender_map: Optional[Dict[str, str]] = None,
    competitor_id_map: Optional[Dict[str, str]] = None,
) -> List[CompetitorRecord]:
    """
    Convert STRATHEX historical rows into STRATHMARK ``CompetitorRecord`` objects.

    ``tournament_results`` remains in the signature for source compatibility,
    but STRATHMARK v2 deliberately ignores same-tournament context. The field
    calculation uses only evidence dated before its explicit cutoff.
    """
    if results_df is None:
        results_df = pd.DataFrame()

    df = results_df.copy()
    df.columns = [str(col).strip().lower() for col in df.columns]
    df.rename(
        columns={
            "event_code": "event",
            "time": "raw_time",
            "actual_time": "raw_time",
            "diameter_mm": "size_mm",
            "diameter": "size_mm",
            "species_code": "species",
            "result_date": "date",
        },
        inplace=True,
    )

    division_by_key = {_name_key(name): value for name, value in (division_map or {}).items()}
    gender_by_key = {_name_key(name): _clean_gender(value) for name, value in (gender_map or {}).items()}
    competitor_id_by_key = {
        _name_key(name): _clean_optional_text(value) for name, value in (competitor_id_map or {}).items()
    }
    del tournament_results

    empty_rows = df.iloc[0:0]
    rows_by_name: Dict[str, pd.DataFrame] = {}
    if "competitor_name" in df.columns:
        df["_strathex_name_key"] = df["competitor_name"].map(_name_key)
        rows_by_name = {
            key: rows.drop(columns=["_strathex_name_key"])
            for key, rows in df.groupby("_strathex_name_key", sort=False)
            if key
        }

    records: List[CompetitorRecord] = []
    for name in competitor_names:
        key = _name_key(name)
        comp_rows = rows_by_name.get(key, empty_rows)

        history: List[HistoricalResult] = []
        for _, row in comp_rows.iterrows():
            try:
                raw_time = float(row.get("raw_time", float("nan")))
                if pd.isna(raw_time) or raw_time <= 0:
                    continue

                event_code = (_clean_optional_text(row.get("event")) or "SB").upper()
                species = _clean_optional_text(row.get("species")) or "Unknown"

                size_value = row.get("size_mm", 300.0)
                size_mm = float(size_value)
                if pd.isna(size_mm) or size_mm <= 0:
                    size_mm = 300.0

                quality_value = row.get("quality", 5)
                quality = int(float(quality_value)) if quality_value is not None and not pd.isna(quality_value) else 5
                quality = max(1, min(10, quality))

                result_date = None
                date_value = row.get("date")
                if date_value is not None and not pd.isna(date_value):
                    try:
                        result_date = resolve_prediction_as_of(date_value, label="historical result date")
                    except (TypeError, ValueError):
                        result_date = None
                if result_date is not None and pd.isna(result_date):
                    result_date = None

                field_strength = row.get("field_strength")
                if field_strength is not None and not pd.isna(field_strength):
                    field_strength = float(field_strength)
                else:
                    field_strength = None

                history.append(
                    HistoricalResult(
                        event_code=event_code,
                        time_seconds=raw_time,
                        species=species,
                        diameter_mm=size_mm,
                        quality=quality,
                        result_date=result_date,
                        heat_id=_clean_optional_text(row.get("heat_id")),
                        field_strength=field_strength,
                    )
                )
            except (TypeError, ValueError, OverflowError):
                continue

        gender = gender_by_key.get(key)
        if gender is None and "gender" in comp_rows.columns:
            for value in comp_rows["gender"]:
                gender = _clean_gender(value)
                if gender:
                    break

        competitor_id = competitor_id_by_key.get(key)
        if competitor_id is None and "competitor_id" in comp_rows.columns:
            for value in comp_rows["competitor_id"]:
                competitor_id = _clean_optional_text(value)
                if competitor_id:
                    break

        records.append(
            CompetitorRecord(
                name=str(name),
                history=history,
                division=division_by_key.get(key),
                gender=gender,
                competitor_id=competitor_id,
            )
        )

    return records


def build_wood_profile(species: str, diameter: float, quality: int) -> WoodProfile:
    """Create the STRATHMARK wood value object at the integration boundary."""
    return WoodProfile(
        species=str(species),
        diameter_mm=float(diameter),
        quality=max(1, min(10, int(quality))),
    )


# ---------------------------------------------------------------------------
# Prediction and mark calculation
# ---------------------------------------------------------------------------


def _display_method_name(method: Optional[str]) -> str:
    names = {
        "manual": "Manual",
        "ml": "V2 Residual",
        "baseline": "V2 Core",
        "panel": "V2 Prior",
        "championship": "Championship",
    }
    key = str(method or "").strip().lower()
    return names.get(key, str(method or "Unknown"))


def _value(record: Any, key: str, default: Any = None) -> Any:
    """Read one field from a STRATHMARK object or decoded API mapping."""
    if isinstance(record, Mapping):
        return record.get(key, default)
    return getattr(record, key, default)


def _interval_to_dict(interval: Any) -> Optional[Dict[str, Any]]:
    if interval is None:
        return None
    try:
        lower = float(_value(interval, "lower"))
        upper = float(_value(interval, "upper"))
        nominal_coverage = float(_value(interval, "nominal_coverage"))
    except (TypeError, ValueError) as exc:
        raise RuntimeError("STRATHMARK calculation returned an invalid prediction interval") from exc
    calibration_state = _value(interval, "calibration_state")
    scope = _value(interval, "scope")
    if (
        not all(math.isfinite(value) for value in (lower, upper, nominal_coverage))
        or lower <= 0
        or upper <= 0
        or lower > upper
        or not 0 < nominal_coverage < 1
        or not _is_safe_output_text(calibration_state)
        or not _is_safe_output_text(scope)
    ):
        raise RuntimeError("STRATHMARK calculation returned an invalid prediction interval")
    return {
        "lower": lower,
        "upper": upper,
        "nominal_coverage": nominal_coverage,
        "calibration_state": calibration_state,
        "scope": scope,
    }


def _iso_date(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is not None:
            value = value.astimezone(timezone.utc)
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    text = str(value).strip()
    return text or None


def resolve_calculation_transport(value: Optional[str] = None) -> str:
    """Return the explicitly selected STRATHMARK calculation transport."""
    transport = str(value or os.environ.get("STRATHMARK_TRANSPORT", "python")).strip().lower()
    if transport not in {"python", "http"}:
        raise ValueError("STRATHMARK transport must be 'python' or 'http'")
    return transport


def _resolve_timeout_seconds() -> float:
    raw = os.environ.get("STRATHMARK_API_TIMEOUT_SECONDS", str(_DEFAULT_API_TIMEOUT_SECONDS))
    try:
        timeout = float(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError("STRATHMARK_API_TIMEOUT_SECONDS must be numeric") from exc
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("STRATHMARK_API_TIMEOUT_SECONDS must be finite and greater than zero")
    return timeout


def _resolve_api_url(value: Optional[str]) -> str:
    api_url = str(value or os.environ.get("STRATHMARK_API_URL", "")).strip().rstrip("/")
    if not api_url:
        raise ValueError("STRATHMARK_API_URL is required when STRATHMARK_TRANSPORT=http")

    parsed = urlparse(api_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("STRATHMARK_API_URL must be an absolute HTTP(S) URL")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("STRATHMARK_API_URL must not contain credentials")
    if parsed.path not in {"", "/"}:
        raise ValueError("STRATHMARK_API_URL must not contain a path")
    if parsed.query or parsed.fragment:
        raise ValueError("STRATHMARK_API_URL must not contain a query string or fragment")
    if parsed.scheme == "http" and parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("Remote STRATHMARK API URLs must use HTTPS")
    return api_url


def describe_api_endpoint(value: Optional[str] = None) -> str:
    """Return a validated, credential-free endpoint label for operator logs."""
    parsed = urlparse(_resolve_api_url(value))
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("STRATHMARK_API_URL contains an invalid port") from exc
    host = f"[{parsed.hostname}]" if ":" in str(parsed.hostname) else str(parsed.hostname)
    return f"{parsed.scheme}://{host}{f':{port}' if port is not None else ''}"


def _validate_text(value: Any, field: str, *, maximum: int, optional: bool = False) -> None:
    if value is None and optional:
        return
    text = str(value or "").strip()
    if not text or len(text) > maximum:
        requirement = f"1-{maximum} characters"
        raise ValueError(f"{field} must contain {requirement}")


def _validate_time(value: Any, field: str, *, optional: bool = False) -> None:
    if value is None and optional:
        return
    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be numeric") from exc
    if not _MIN_TIME_SECONDS <= numeric <= _MAX_TIME_SECONDS:
        raise ValueError(f"{field} must be between 3 and 180 seconds")


def _validate_field_request(
    competitor_records: List[CompetitorRecord],
    wood: WoodProfile,
    event_code: str,
) -> None:
    """Apply the HTTP field contract before either transport is selected."""
    if not competitor_records:
        raise ValueError("STRATHMARK field must contain at least one competitor")
    if len(competitor_records) > MAX_STRATHMARK_FIELD_SIZE:
        raise ValueError("STRATHMARK fields are limited to 64 competitors")

    _validate_text(wood.species, "wood species", maximum=100)
    if not _MIN_DIAMETER_MM <= float(wood.diameter_mm) <= _MAX_DIAMETER_MM:
        raise ValueError("wood diameter must be between 225 and 500 mm")
    if not 1 <= int(wood.quality) <= 10:
        raise ValueError("wood quality must be between 1 and 10")
    if event_code not in {"SB", "UH"}:
        raise ValueError("event_code must be SB or UH")

    for record in competitor_records:
        _validate_text(record.name, "competitor name", maximum=100)
        _validate_text(record.competitor_id, "competitor_id", maximum=128, optional=True)
        _validate_text(record.division, "division", maximum=100, optional=True)
        if record.gender not in {None, "M", "F"}:
            raise ValueError("competitor gender must be M or F")
        _validate_time(record.manual_time_override, "manual_time_override", optional=True)
        for result in record.history:
            history_event = str(result.event_code).strip().upper()
            if history_event not in {"SB", "UH"}:
                raise ValueError("history event_code must be SB or UH")
            _validate_time(result.time_seconds, "history time_seconds")
            _validate_text(result.species, "history species", maximum=100)
            if not _MIN_DIAMETER_MM <= float(result.diameter_mm) <= _MAX_DIAMETER_MM:
                raise ValueError("history diameter must be between 225 and 500 mm")
            if not 1 <= int(result.quality) <= 10:
                raise ValueError("history quality must be between 1 and 10")
            _validate_text(result.heat_id, "history heat_id", maximum=100, optional=True)


def _validate_http_contract(document: Any) -> None:
    """Require the audited v2 calculation request and response schemas."""
    if not isinstance(document, Mapping):
        raise RuntimeError("STRATHMARK API returned an invalid OpenAPI document")
    api_version = document.get("info", {}).get("version")
    if api_version != _STRATHMARK_API_VERSION:
        raise RuntimeError(
            f"STRATHEX requires STRATHMARK API {_STRATHMARK_API_VERSION}; server reported {api_version!r}"
        )

    calculate = document.get("paths", {}).get("/calculate", {}).get("post", {})
    request_schema = (
        calculate.get("requestBody", {}).get("content", {}).get("application/json", {}).get("schema", {}).get("$ref")
    )
    response_schema = (
        calculate.get("responses", {}).get("200", {}).get("content", {}).get("application/json", {}).get("schema", {})
    )
    schemas = document.get("components", {}).get("schemas", {})
    if (
        request_schema != "#/components/schemas/LegacyCalculateRequest"
        or response_schema.get("type") != "array"
        or response_schema.get("items", {}).get("$ref") != "#/components/schemas/MarkResultResponse"
        or "LegacyCalculateRequest" not in schemas
        or "MarkResultResponse" not in schemas
    ):
        raise RuntimeError("STRATHMARK API does not expose the required v2 /calculate field contract")


def _reject_http_redirect(response: Any) -> None:
    status_code = int(getattr(response, "status_code", 200))
    if 300 <= status_code < 400:
        raise RuntimeError("STRATHMARK API redirects are not allowed")


def _bounded_response_json(response: Any, *, label: str) -> Any:
    """Decode one API response without accepting an unbounded body."""
    headers = getattr(response, "headers", {}) or {}
    raw_content_length = headers.get("Content-Length") or headers.get("content-length")
    if raw_content_length is not None:
        try:
            content_length = int(raw_content_length)
        except (TypeError, ValueError) as exc:
            raise RuntimeError(f"STRATHMARK API {label} returned an invalid Content-Length") from exc
        if content_length < 0 or content_length > _MAX_API_RESPONSE_BYTES:
            raise RuntimeError(f"STRATHMARK API {label} exceeded the response size limit")

    close = getattr(response, "close", None)
    try:
        if hasattr(response, "iter_content"):
            chunks: list[bytes] = []
            size = 0
            for chunk in response.iter_content(chunk_size=64 * 1024):
                if not chunk:
                    continue
                size += len(chunk)
                if size > _MAX_API_RESPONSE_BYTES:
                    raise RuntimeError(f"STRATHMARK API {label} exceeded the response size limit")
                chunks.append(chunk)
            return json.loads(b"".join(chunks))

        content = getattr(response, "content", None)
        if content is not None:
            if len(content) > _MAX_API_RESPONSE_BYTES:
                raise RuntimeError(f"STRATHMARK API {label} exceeded the response size limit")
            return json.loads(content)

        # Lightweight test doubles may expose only json(). Production requests
        # responses always take the bounded streaming path above.
        return response.json()
    finally:
        if callable(close):
            close()


def _serialize_history(history: List[HistoricalResult]) -> List[Dict[str, Any]]:
    return [
        {
            "event_code": str(item.event_code).strip().upper(),
            "time_seconds": float(item.time_seconds),
            "species": str(item.species),
            "diameter_mm": float(item.diameter_mm),
            "quality": int(item.quality),
            "result_date": _iso_date(item.result_date),
            "heat_id": item.heat_id,
        }
        for item in history
    ]


def _serialize_competitor(record: CompetitorRecord) -> Dict[str, Any]:
    return {
        "name": str(record.name),
        "competitor_id": record.competitor_id,
        "gender": record.gender,
        "division": record.division,
        "manual_time_override": record.manual_time_override,
        "history": _serialize_history(record.history),
    }


def _calculate_over_http(
    competitor_records: List[CompetitorRecord],
    wood: WoodProfile,
    event_code: str,
    prediction_as_of: date,
    api_url: Optional[str],
) -> List[SimpleNamespace]:
    base_url = _resolve_api_url(api_url)
    timeout = _resolve_timeout_seconds()

    try:
        contract_response = requests.get(
            f"{base_url}/openapi.json",
            timeout=timeout,
            allow_redirects=False,
            stream=True,
        )
        _reject_http_redirect(contract_response)
        contract_response.raise_for_status()
        _validate_http_contract(_bounded_response_json(contract_response, label="contract response"))
    except (requests.RequestException, TypeError, ValueError, AttributeError) as exc:
        raise RuntimeError(f"STRATHMARK API contract check failed: {exc}") from exc

    payload = {
        "competitors": [_serialize_competitor(record) for record in competitor_records],
        "wood": {
            "species": str(wood.species),
            "diameter_mm": float(wood.diameter_mm),
            "quality": int(wood.quality),
        },
        "event_code": event_code,
        "prediction_as_of": prediction_as_of.isoformat(),
    }

    try:
        response = requests.post(
            f"{base_url}/calculate",
            json=payload,
            timeout=timeout,
            allow_redirects=False,
            stream=True,
        )
        _reject_http_redirect(response)
        response.raise_for_status()
        decoded = _bounded_response_json(response, label="calculation response")
    except (requests.RequestException, TypeError, ValueError, AttributeError) as exc:
        raise RuntimeError(f"STRATHMARK API calculation failed: {exc}") from exc

    if not isinstance(decoded, list) or len(decoded) != len(competitor_records):
        raise RuntimeError("STRATHMARK API returned an invalid field response")

    output: List[SimpleNamespace] = []
    for row in decoded:
        if not isinstance(row, Mapping):
            raise RuntimeError("STRATHMARK API returned a non-object result")
        if row.get("engine_version") != _STRATHMARK_API_VERSION:
            raise RuntimeError("STRATHMARK API calculation did not return the required v2 engine metadata")
        output.append(SimpleNamespace(**row))
    return output


def _result_identity_key(record: Any) -> str:
    competitor_id = _clean_optional_text(_value(record, "competitor_id"))
    if competitor_id:
        return f"id:{competitor_id}"
    name_key = _name_key(_value(record, "name"))
    if name_key:
        return f"name:{name_key}"
    raise RuntimeError("STRATHMARK result is missing competitor identity")


def _has_field(record: Any, key: str) -> bool:
    if isinstance(record, Mapping):
        return key in record
    return hasattr(record, key)


def _is_safe_output_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip()) and value.isprintable()


def _validate_result_contract(record: Any, *, expected_evidence_cutoff: date) -> date:
    """Reject malformed v2 evidence before it reaches judge-facing output."""
    for field in ("name", "method_used", "confidence", "explanation"):
        value = _value(record, field)
        if not _is_safe_output_text(value):
            raise RuntimeError(f"STRATHMARK calculation returned invalid {field}")

    mark = _value(record, "mark")
    if (
        isinstance(mark, bool)
        or not isinstance(mark, int)
        or not _sm_rules.MIN_MARK_SECONDS <= mark <= _sm_rules.MAX_MARK_SECONDS
    ):
        raise RuntimeError("STRATHMARK calculation returned an invalid legal mark")

    try:
        predicted_time = float(_value(record, "predicted_time"))
    except (TypeError, ValueError) as exc:
        raise RuntimeError("STRATHMARK calculation returned an invalid predicted_time") from exc
    if not math.isfinite(predicted_time) or predicted_time <= 0:
        raise RuntimeError("STRATHMARK calculation returned an invalid predicted_time")

    std_dev = _value(record, "std_dev")
    if std_dev is not None:
        try:
            numeric_std_dev = float(std_dev)
        except (TypeError, ValueError) as exc:
            raise RuntimeError("STRATHMARK calculation returned an invalid std_dev") from exc
        if not math.isfinite(numeric_std_dev) or numeric_std_dev <= 0:
            raise RuntimeError("STRATHMARK calculation returned an invalid std_dev")

    method = str(_value(record, "method_used")).strip().lower()
    provenance = _value(record, "provenance")
    if method == "manual":
        if (
            not isinstance(provenance, Mapping)
            or provenance.get("source") != "operator_override"
            or provenance.get("model_evidence") is not False
        ):
            raise RuntimeError("STRATHMARK calculation returned invalid manual-override provenance")
        if any(_value(record, field) is not None for field in ("model_version", "calibration_version", "interval")):
            raise RuntimeError("STRATHMARK calculation returned invalid manual-override model metadata")
    else:
        for field in ("model_version", "calibration_version"):
            if not _is_safe_output_text(_value(record, field)):
                raise RuntimeError(f"STRATHMARK calculation returned invalid {field}")
    if not _is_safe_output_text(_value(record, "optimizer")):
        raise RuntimeError("STRATHMARK calculation returned invalid optimizer")

    raw_evidence_cutoff = _value(record, "evidence_cutoff")
    if raw_evidence_cutoff is None:
        raise RuntimeError("STRATHMARK calculation returned invalid evidence_cutoff")
    try:
        evidence_cutoff = resolve_prediction_as_of(raw_evidence_cutoff, label="result evidence_cutoff")
    except ValueError as exc:
        raise RuntimeError("STRATHMARK calculation returned invalid evidence_cutoff") from exc
    if evidence_cutoff != expected_evidence_cutoff:
        raise RuntimeError("STRATHMARK calculation returned evidence_cutoff that does not match the requested cutoff")

    if not isinstance(_value(record, "degraded"), bool):
        raise RuntimeError("STRATHMARK calculation returned invalid degraded metadata")
    return evidence_cutoff


def mark_results_to_dicts(
    mark_results: Any,
    *,
    transport: str,
    expected_evidence_cutoff: date,
    expected_competitors: Optional[List[CompetitorRecord]] = None,
) -> List[Dict[str, Any]]:
    """Preserve STRATHMARK v2 prediction, uncertainty, and optimizer evidence."""
    expected_keys = (
        [_result_identity_key(record) for record in expected_competitors] if expected_competitors is not None else []
    )
    expected_names_by_key = (
        {_result_identity_key(record): str(record.name).strip() for record in expected_competitors}
        if expected_competitors is not None
        else {}
    )
    expected_records_by_key = (
        {_result_identity_key(record): record for record in expected_competitors}
        if expected_competitors is not None
        else {}
    )
    if len(expected_keys) != len(set(expected_keys)):
        raise ValueError("STRATHMARK field contains duplicate competitor identities")
    expected_key_set = set(expected_keys)
    seen_keys: set[str] = set()
    field_execution_bundle: Optional[tuple[str, str, str]] = None
    field_prediction_bundle: Optional[tuple[str, str]] = None
    output: List[Dict[str, Any]] = []

    for mark_result in mark_results:
        missing_fields = sorted(field for field in _REQUIRED_RESULT_FIELDS if not _has_field(mark_result, field))
        if missing_fields:
            raise RuntimeError("STRATHMARK calculation omitted required audit fields: " + ", ".join(missing_fields))
        evidence_cutoff = _validate_result_contract(
            mark_result,
            expected_evidence_cutoff=expected_evidence_cutoff,
        )
        if _value(mark_result, "engine_version") != _STRATHMARK_API_VERSION:
            raise RuntimeError("STRATHMARK calculation did not return the required v2 engine metadata")
        result_execution_bundle = (
            str(_value(mark_result, "engine_version")),
            evidence_cutoff.isoformat(),
            str(_value(mark_result, "optimizer")),
        )
        if field_execution_bundle is None:
            field_execution_bundle = result_execution_bundle
        elif result_execution_bundle != field_execution_bundle:
            raise RuntimeError("STRATHMARK calculation returned mixed model snapshots for one field")
        if str(_value(mark_result, "method_used")).strip().lower() != "manual":
            result_prediction_bundle = (
                str(_value(mark_result, "model_version")),
                str(_value(mark_result, "calibration_version")),
            )
            if field_prediction_bundle is None:
                field_prediction_bundle = result_prediction_bundle
            elif result_prediction_bundle != field_prediction_bundle:
                raise RuntimeError("STRATHMARK calculation returned mixed model snapshots for one field")
        identity_key = _result_identity_key(mark_result)
        if expected_key_set and identity_key not in expected_key_set:
            raise RuntimeError("STRATHMARK calculation returned an unexpected competitor identity")
        expected_name = expected_names_by_key.get(identity_key)
        returned_name = str(_value(mark_result, "name")).strip()
        if expected_name is not None and _name_key(returned_name) != _name_key(expected_name):
            raise RuntimeError("STRATHMARK calculation returned a mismatched competitor name")
        if identity_key in seen_keys:
            raise RuntimeError("STRATHMARK calculation returned a duplicate competitor identity")
        seen_keys.add(identity_key)

        raw_method = str(_value(mark_result, "method_used", "unknown"))
        expected_record = expected_records_by_key.get(identity_key)
        if expected_record is not None:
            manual_override = expected_record.manual_time_override
            if manual_override is None and raw_method.strip().lower() == "manual":
                raise RuntimeError("STRATHMARK calculation returned an unexpected manual override")
            if manual_override is not None:
                if raw_method.strip().lower() != "manual" or not math.isclose(
                    float(_value(mark_result, "predicted_time")),
                    float(manual_override),
                    rel_tol=0.0,
                    abs_tol=1e-9,
                ):
                    raise RuntimeError("STRATHMARK calculation did not honor the requested manual override")
        interval = _interval_to_dict(_value(mark_result, "interval"))
        std_dev_value = _value(mark_result, "std_dev")
        std_dev = float(std_dev_value) if std_dev_value is not None else 3.0
        warnings = _value(mark_result, "warnings")
        optimizer_metadata = _value(mark_result, "optimizer_metadata")
        provenance = _value(mark_result, "provenance")
        ignored_factors = _value(mark_result, "ignored_factors")
        if not isinstance(warnings, list) or not isinstance(ignored_factors, list):
            raise RuntimeError("STRATHMARK calculation returned invalid warning metadata")
        if not all(_is_safe_output_text(item) for item in warnings + ignored_factors):
            raise RuntimeError("STRATHMARK calculation returned unsafe warning metadata")
        if not isinstance(optimizer_metadata, Mapping) or not isinstance(provenance, Mapping):
            raise RuntimeError("STRATHMARK calculation returned invalid provenance metadata")
        selected_prediction = {
            "time": float(_value(mark_result, "predicted_time")),
            "confidence": _value(mark_result, "confidence"),
            "explanation": _value(mark_result, "explanation"),
            "interval": interval,
            "error": None,
            "std_dev": std_dev,
        }

        output.append(
            {
                "name": expected_name or returned_name,
                "competitor_id": _value(mark_result, "competitor_id"),
                "mark": int(_value(mark_result, "mark")),
                "predicted_time": float(_value(mark_result, "predicted_time")),
                "method_used": _display_method_name(raw_method),
                "method_key": raw_method,
                "confidence": _value(mark_result, "confidence"),
                "explanation": _value(mark_result, "explanation"),
                "predictions": {"v2": selected_prediction},
                "prediction_interval": interval,
                "performance_std_dev": std_dev,
                "std_dev": std_dev,
                "engine_version": _value(mark_result, "engine_version"),
                "model_version": _value(mark_result, "model_version"),
                "calibration_version": _value(mark_result, "calibration_version"),
                "evidence_cutoff": evidence_cutoff.isoformat(),
                "optimizer": _value(mark_result, "optimizer"),
                "optimizer_metadata": dict(optimizer_metadata),
                "warnings": list(warnings),
                "degraded": bool(_value(mark_result, "degraded")),
                "provenance": dict(provenance),
                "ignored_factors": list(ignored_factors),
                "prediction_id": _value(mark_result, "prediction_id"),
                "ledger_recorded": _value(mark_result, "ledger_recorded"),
                "ledger_status": _value(mark_result, "ledger_status"),
                "transport": transport,
            }
        )

    if expected_key_set and seen_keys != expected_key_set:
        raise RuntimeError("STRATHMARK calculation omitted one or more competitor results")
    return output


def calculate_handicap_results(
    competitor_records: List[CompetitorRecord],
    wood: WoodProfile,
    event_code: str,
    results_df: Optional[pd.DataFrame],
    wood_df: Optional[pd.DataFrame] = None,
    tournament_results: Optional[Dict[str, float]] = None,
    ollama_url: str = "http://localhost:11434",
    prediction_as_of: Any = None,
    transport: Optional[str] = None,
    api_url: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Calculate one field through the selected STRATHMARK v2 transport."""
    del results_df, wood_df, tournament_results, ollama_url
    event_code = str(event_code).strip().upper()
    _validate_field_request(competitor_records, wood, event_code)
    cutoff = resolve_prediction_as_of(prediction_as_of)
    selected_transport = resolve_calculation_transport(transport)

    if selected_transport == "http":
        mark_results = _calculate_over_http(
            competitor_records,
            wood,
            event_code,
            cutoff,
            api_url,
        )
    else:
        calculator = HandicapCalculator()
        mark_results = calculator.calculate(
            competitors=competitor_records,
            wood=wood,
            event_code=event_code,
            context=PredictionContext(prediction_as_of=cutoff),
        )

    return mark_results_to_dicts(
        mark_results,
        transport=selected_transport,
        expected_evidence_cutoff=cutoff,
        expected_competitors=competitor_records,
    )


# ---------------------------------------------------------------------------
# Persistence boundary
# ---------------------------------------------------------------------------


def _validate_sqlite_backup(path: Path) -> None:
    connection = None
    try:
        connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
        result = connection.execute("PRAGMA integrity_check").fetchone()
    except sqlite3.Error as exc:
        raise RuntimeError(f"STRATHMARK backup is not a readable SQLite database: {path}") from exc
    finally:
        if connection is not None:
            connection.close()
    if result != ("ok",):
        raise RuntimeError(f"STRATHMARK backup failed SQLite integrity validation: {path}")


def _create_atomic_store_backup(store_path: Path, backup_path: Path) -> None:
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{backup_path.name}.",
        suffix=".tmp",
        dir=backup_path.parent,
    )
    os.close(descriptor)
    temporary_path = Path(temporary_name)
    try:
        source = sqlite3.connect(store_path)
        target = sqlite3.connect(temporary_path)
        try:
            source.backup(target)
        finally:
            target.close()
            source.close()
        with temporary_path.open("r+b") as backup_file:
            backup_file.flush()
            os.fsync(backup_file.fileno())
        _validate_sqlite_backup(temporary_path)
        os.replace(temporary_path, backup_path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def create_result_store() -> ResultStore:
    """Atomically back up a legacy store, then let STRATHMARK v2 migrate it."""
    configured_path = str(os.environ.get("STRATHMARK_DB_PATH", "")).strip()
    raw_path = Path(configured_path).expanduser() if configured_path else Path.home() / ".strathmark" / "results.db"
    store_path = raw_path.resolve(strict=False)
    backup_path = store_path.with_suffix(store_path.suffix + ".pre-v2.bak")
    if backup_path.exists():
        _validate_sqlite_backup(backup_path)
    elif store_path.is_file():
        _create_atomic_store_backup(store_path, backup_path)
        _log.warning("Created pre-v2 STRATHMARK store backup at %s", backup_path)
    return ResultStore(db_path=store_path)


def record_round_results(
    round_object: Dict[str, Any],
    wood_selection: Dict[str, Any],
    store: ResultStore,
    *,
    competition_id: Optional[str] = None,
    result_date: Optional[date] = None,
) -> int:
    """Write a completed tournament round to the STRATHMARK result store."""
    actual_results = round_object.get("actual_results") or round_object.get("results") or {}
    if not actual_results:
        return 0

    round_name = round_object.get("round_name", "")
    event_code = str(wood_selection.get("event", "SB")).strip().upper()
    species = str(wood_selection.get("species", "Unknown"))
    diameter_mm = float(wood_selection.get("size_mm", 300))
    quality = int(wood_selection.get("quality", 5))
    heat_id = round_name.replace(" ", "-").replace("/", "-") if round_name else ""

    inserted = 0
    for competitor_name, time_seconds in actual_results.items():
        if time_seconds is None:
            continue
        try:
            if store.record_result(
                competitor_name=str(competitor_name),
                event_code=event_code,
                time_seconds=float(time_seconds),
                species=species,
                diameter_mm=diameter_mm,
                quality=quality,
                heat_id=heat_id,
                competition_id=competition_id,
                result_date=result_date,
            ):
                inserted += 1
        except Exception as exc:
            _log.warning("Could not persist result for %s: %s", competitor_name, exc)

    return inserted


def migrate_excel_to_store(results_df: pd.DataFrame, store: ResultStore) -> int:
    """Idempotently import the Excel history into STRATHMARK's result store."""
    if results_df is None or results_df.empty:
        return 0
    return store.import_from_dataframe(results_df, skip_duplicates=True)


# ---------------------------------------------------------------------------
# Simulation and fairness compatibility facades
# ---------------------------------------------------------------------------


def get_competitor_variance_seconds(comp: Dict[str, Any]) -> float:
    """Isolate the pinned STRATHMARK private variance helper in one boundary."""
    return float(_sm_variance._get_competitor_variance_seconds(comp))


def run_monte_carlo_simulation_engine(
    competitors_with_marks: List[Dict[str, Any]],
    **kwargs,
) -> Dict[str, Any]:
    return _sm_variance.run_monte_carlo_simulation(
        competitors_with_marks,
        **kwargs,
    )


def get_ai_assessment_engine(analysis: Dict[str, Any]) -> str:
    return _sm_assess_handicaps(analysis)


def get_championship_analysis_engine(
    analysis: Dict[str, Any],
    predictions: List[Dict],
) -> str:
    return _sm_championship_analysis(analysis, predictions)


def simulate_and_assess_engine(
    competitors_with_marks: List[Dict[str, Any]],
    *,
    num_simulations: Optional[int] = None,
    show: bool = True,
):
    return _sm_simulate_and_assess(
        competitors_with_marks,
        num_simulations=num_simulations,
        show=show,
    )
