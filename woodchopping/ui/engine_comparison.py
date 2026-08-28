"""Deterministic, observational engine-comparison evidence for completed competitions."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

_ID = re.compile(r"^[a-z][a-z0-9_.-]{0,31}:[A-Za-z0-9][A-Za-z0-9_.:@/-]{0,94}$")
_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_COMMIT = re.compile(r"^[0-9a-f]{7,40}$")
_TOKEN = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_SENSITIVE = re.compile(
    r"(?:authorization|bearer\s|credential|password|private[_ -]?key|secret|smv3\.)",
    re.IGNORECASE,
)
_PREDICTION_FIELDS = frozenset({"competitor_id", "predicted_completion_ms", "predicted_mark"})
_OUTCOME_FIELDS = frozenset({"competitor_id", "actual_completion_ms", "placing", "result_status"})
_REVIEW_FIELDS = frozenset({"field_id", "classification", "interventions"})
_CLASSIFICATIONS = ("amber", "green", "red", "unknown")


def build_engine_comparison_record(
    *,
    competition_id: str,
    requested_engine: str,
    requested_mode: str,
    returned_engine: str | None,
    returned_model_ids: Sequence[str] | None,
    returned_bundle_ids: Sequence[str] | None,
    returned_contract_version: str | None,
    returned_contract_digest: str | None,
    returned_source_commit: str | None,
    predictions: Sequence[Mapping[str, Any]],
    outcomes: Sequence[Mapping[str, Any]],
    reviews: Sequence[Mapping[str, Any]],
    timing_ms: Mapping[str, int | None] | None,
    failure_count: int | None,
    recovery_count: int | None,
    judge_feedback: str | None,
) -> dict[str, Any]:
    """Build one JSON-safe comparison record without ranking either engine.

    The caller supplies only pseudonymous sporting identities and bounded outcome facts.
    Missing evidence remains explicitly unknown. This function intentionally has no score,
    recommendation, winner, or default-selection output.
    """

    _require_id(competition_id, {"competition", "tournament"}, "competition")
    if requested_engine not in {"v2", "v3"}:
        raise ValueError("requested engine is invalid")
    if requested_mode not in {"production", "rehearsal"}:
        raise ValueError("requested mode is invalid")
    if returned_engine is not None and returned_engine not in {"v2", "v3"}:
        raise ValueError("returned engine is invalid")

    returned_models = _optional_ids(returned_model_ids, "model", "returned model")
    returned_bundles = _optional_ids(returned_bundle_ids, "bundle", "returned bundle")
    contract_version = _optional_text(returned_contract_version, "returned contract version", maximum=128)
    contract_digest = _optional_pattern(returned_contract_digest, _DIGEST, "returned contract digest")
    source_commit = _optional_pattern(returned_source_commit, _COMMIT, "returned source commit")

    predictions_by_id = _prediction_rows(predictions)
    outcomes_by_id = _outcome_rows(outcomes)
    comparison_rows = [
        _comparison_row(
            competitor_id,
            predictions_by_id.get(competitor_id),
            outcomes_by_id.get(competitor_id),
        )
        for competitor_id in sorted(predictions_by_id.keys() | outcomes_by_id.keys())
    ]
    review_summary = _review_summary(reviews)
    timing = _timing(timing_ms)
    feedback = _optional_text(judge_feedback, "judge feedback", maximum=2000)

    payload: dict[str, Any] = {
        "schema_version": "strathex-engine-comparison-v1",
        "comparison_purpose": "observational_only",
        "competition_id": competition_id,
        "requested_authority": {
            "engine": requested_engine,
            "mode": requested_mode,
        },
        "returned_authority": {
            "engine": _known(returned_engine),
            "model_ids": _known(returned_models),
            "bundle_ids": _known(returned_bundles),
            "contract_version": _known(contract_version),
            "contract_digest": _known(contract_digest),
            "source_commit": _known(source_commit),
        },
        "predictions_vs_outcomes": comparison_rows,
        "review_summary": review_summary,
        "timing_ms": timing,
        "operational_counts": {
            "failure_count": _known(_optional_count(failure_count, "failure count")),
            "recovery_count": _known(_optional_count(recovery_count, "recovery count")),
        },
        "judge_feedback": feedback,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {**payload, "record_digest": hashlib.sha256(encoded).hexdigest()}


def build_engine_comparison_from_completed_state(
    state: Mapping[str, Any],
    *,
    authority: Any,
    judge_feedback: str | None = None,
) -> dict[str, Any]:
    """Derive one factual comparison record from completed local scope evidence."""
    competition_id = str(authority.reference.scope_id)
    predictions: list[dict[str, Any]] = []
    outcomes: list[dict[str, Any]] = []
    returned_engines: set[str] = set()
    returned_models: set[str] = set()
    returned_bundles: set[str] = set()

    events = state.get("events")
    if isinstance(events, list):
        round_containers = [
            (event_index, event.get("rounds", ()))
            for event_index, event in enumerate(events)
            if isinstance(event, Mapping)
        ]
    else:
        round_containers = [(-1, state.get("rounds", ()))]
    for event_index, rounds in round_containers:
        if not isinstance(rounds, Sequence) or isinstance(rounds, (str, bytes)):
            continue
        for round_index, round_object in enumerate(rounds):
            if not isinstance(round_object, Mapping) or round_object.get("status") != "completed":
                continue
            actual_results = round_object.get("actual_results")
            actual_results = actual_results if isinstance(actual_results, Mapping) else {}
            finish_order = round_object.get("finish_order")
            finish_order = finish_order if isinstance(finish_order, Mapping) else {}
            rows = round_object.get("handicap_results")
            if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes)):
                continue
            for row_index, row in enumerate(rows):
                if not isinstance(row, Mapping):
                    continue
                source_competitor_id = row.get("competitor_id")
                if not isinstance(source_competitor_id, str) or not source_competitor_id.startswith("competitor:"):
                    continue
                observation_id = _observation_competitor_id(
                    competition_id,
                    event_index,
                    round_index,
                    row_index,
                    source_competitor_id,
                    row.get("receipt_id"),
                )
                mark = _coerce_nonnegative_int(row.get("mark"))
                predicted_raw_ms = _seconds_to_ms(row.get("predicted_time"))
                predicted_completion_ms = (
                    None if mark is None or predicted_raw_ms is None else mark * 1000 + predicted_raw_ms
                )
                predictions.append(
                    {
                        "competitor_id": observation_id,
                        "predicted_completion_ms": predicted_completion_ms,
                        "predicted_mark": mark,
                    }
                )

                display_key = row.get("name")
                actual_raw_ms = _seconds_to_ms(actual_results.get(display_key))
                actual_completion_ms = None if mark is None or actual_raw_ms is None else mark * 1000 + actual_raw_ms
                placing = _coerce_positive_int(finish_order.get(display_key))
                outcomes.append(
                    {
                        "competitor_id": observation_id,
                        "actual_completion_ms": actual_completion_ms,
                        "placing": placing,
                        "result_status": "completion" if actual_raw_ms is not None else None,
                    }
                )
                returned_engine = _row_engine(row)
                if returned_engine is not None:
                    returned_engines.add(returned_engine)
                returned_models.update(_namespaced_values(row.get("model_ids"), "model:"))
                returned_bundles.update(_namespaced_values(row.get("bundles"), "bundle:"))

    operational = state.get("prediction_engine_operational_counts")
    operational = operational if isinstance(operational, Mapping) else {}
    timing = state.get("prediction_engine_timing_ms")
    timing = timing if isinstance(timing, Mapping) else None
    if timing is None:
        timing = _authority_timing(authority)
    reviews = state.get("prediction_review_evidence")
    reviews = reviews if isinstance(reviews, Sequence) and not isinstance(reviews, (str, bytes)) else ()
    contract_identity = str(authority.contract_identity or "")
    source_identity = str(authority.source_identity or "")
    source_commit = source_identity.removeprefix("strathmark:")

    return build_engine_comparison_record(
        competition_id=competition_id,
        requested_engine=str(authority.engine),
        requested_mode=str(authority.mode),
        returned_engine=next(iter(returned_engines)) if len(returned_engines) == 1 else None,
        returned_model_ids=sorted(returned_models) or None,
        returned_bundle_ids=sorted(returned_bundles) or None,
        returned_contract_version=_valid_optional_text(state.get("returned_contract_version")),
        returned_contract_digest=contract_identity if _DIGEST.fullmatch(contract_identity) else None,
        returned_source_commit=source_commit if _COMMIT.fullmatch(source_commit) else None,
        predictions=predictions,
        outcomes=outcomes,
        reviews=reviews,
        timing_ms=timing,
        failure_count=_coerce_nonnegative_int(operational.get("failure_count")),
        recovery_count=_coerce_nonnegative_int(operational.get("recovery_count")),
        judge_feedback=judge_feedback,
    )


def _observation_competitor_id(
    competition_id: str,
    event_index: int,
    round_index: int,
    row_index: int,
    competitor_id: str,
    receipt_id: Any,
) -> str:
    material = "\0".join(
        (
            competition_id,
            str(event_index),
            str(round_index),
            str(row_index),
            competitor_id,
            str(receipt_id or "unknown"),
        )
    )
    return f"competitor:{hashlib.sha256(material.encode('utf-8')).hexdigest()}"


def _seconds_to_ms(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        return None
    return round(float(value) * 1000)


def _coerce_nonnegative_int(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0 or int(value) != value:
        return None
    return int(value)


def _coerce_positive_int(value: Any) -> int | None:
    result = _coerce_nonnegative_int(value)
    return result if result is not None and result > 0 else None


def _row_engine(row: Mapping[str, Any]) -> str | None:
    returned = row.get("returned_engine")
    if returned in {"v2", "v3"}:
        return str(returned)
    version = str(row.get("engine_version") or "")
    if version.startswith("2."):
        return "v2"
    if version.startswith("3."):
        return "v3"
    return None


def _namespaced_values(value: Any, prefix: str) -> set[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return set()
    return {item for item in value if isinstance(item, str) and item.startswith(prefix) and _ID.fullmatch(item)}


def _valid_optional_text(value: Any) -> str | None:
    if not isinstance(value, str) or not value or len(value.encode("utf-8")) > 128 or _SENSITIVE.search(value):
        return None
    return value


def _authority_timing(authority: Any) -> dict[str, int] | None:
    try:
        selected = datetime.fromisoformat(str(authority.selected_at).replace("Z", "+00:00"))
        locked = datetime.fromisoformat(str(authority.locked_at).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    elapsed_ms = round((locked - selected).total_seconds() * 1000)
    return {"selection_to_lock": elapsed_ms} if elapsed_ms >= 0 else None


def _prediction_rows(rows: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for raw in _require_rows(rows, "prediction"):
        extras = set(raw) - _PREDICTION_FIELDS
        if extras:
            raise ValueError("unsupported prediction field")
        competitor_id = raw.get("competitor_id")
        _require_id(competitor_id, {"competitor"}, "competitor")
        if competitor_id in result:
            raise ValueError("prediction competitor IDs must be unique")
        result[competitor_id] = {
            "predicted_completion_ms": _optional_nonnegative_int(
                raw.get("predicted_completion_ms"), "predicted completion"
            ),
            "predicted_mark": _optional_nonnegative_int(raw.get("predicted_mark"), "predicted mark"),
        }
    return result


def _outcome_rows(rows: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for raw in _require_rows(rows, "outcome"):
        extras = set(raw) - _OUTCOME_FIELDS
        if extras:
            raise ValueError("unsupported outcome field")
        competitor_id = raw.get("competitor_id")
        _require_id(competitor_id, {"competitor"}, "competitor")
        if competitor_id in result:
            raise ValueError("outcome competitor IDs must be unique")
        status = raw.get("result_status")
        if status is not None and (not isinstance(status, str) or _TOKEN.fullmatch(status) is None):
            raise ValueError("result status is invalid")
        result[competitor_id] = {
            "actual_completion_ms": _optional_nonnegative_int(raw.get("actual_completion_ms"), "actual completion"),
            "placing": _optional_positive_int(raw.get("placing"), "placing"),
            "result_status": status,
        }
    return result


def _comparison_row(
    competitor_id: str,
    prediction: Mapping[str, Any] | None,
    outcome: Mapping[str, Any] | None,
) -> dict[str, Any]:
    predicted_ms = None if prediction is None else prediction["predicted_completion_ms"]
    actual_ms = None if outcome is None else outcome["actual_completion_ms"]
    return {
        "competitor_id": competitor_id,
        "prediction_state": "known" if prediction is not None else "unknown",
        "predicted_completion_ms": predicted_ms,
        "predicted_mark": None if prediction is None else prediction["predicted_mark"],
        "outcome_state": "known" if outcome is not None else "unknown",
        "actual_completion_ms": actual_ms,
        "placing": None if outcome is None else outcome["placing"],
        "result_status": None if outcome is None else outcome["result_status"],
        "prediction_error_ms": (None if predicted_ms is None or actual_ms is None else predicted_ms - actual_ms),
    }


def _review_summary(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    fields = []
    classifications: Counter[str] = Counter()
    interventions: Counter[str] = Counter()
    seen: set[str] = set()
    for raw in _require_rows(rows, "review"):
        if set(raw) - _REVIEW_FIELDS:
            raise ValueError("unsupported review field")
        field_id = raw.get("field_id")
        _require_id(field_id, {"field"}, "field")
        if field_id in seen:
            raise ValueError("review field IDs must be unique")
        seen.add(field_id)
        classification = raw.get("classification", "unknown")
        if classification not in _CLASSIFICATIONS:
            raise ValueError("review classification is invalid")
        raw_interventions = raw.get("interventions", ())
        if isinstance(raw_interventions, (str, bytes)) or not isinstance(raw_interventions, Sequence):
            raise ValueError("review interventions must be a sequence")
        canonical_interventions = tuple(sorted(set(raw_interventions)))
        if any(not isinstance(item, str) or _TOKEN.fullmatch(item) is None for item in canonical_interventions):
            raise ValueError("review intervention is invalid")
        classifications[classification] += 1
        interventions.update(canonical_interventions)
        fields.append(
            {
                "field_id": field_id,
                "classification": classification,
                "interventions": list(canonical_interventions),
            }
        )
    return {
        "classification_counts": {key: classifications[key] for key in _CLASSIFICATIONS},
        "fields": sorted(fields, key=lambda item: item["field_id"]),
        "intervention_counts": dict(sorted(interventions.items())),
    }


def _timing(value: Mapping[str, int | None] | None) -> dict[str, Any]:
    if value is None:
        return _known(None)
    if not isinstance(value, Mapping):
        raise ValueError("timing must be a mapping")
    canonical = {}
    for name, duration in sorted(value.items()):
        if not isinstance(name, str) or _TOKEN.fullmatch(name) is None or _SENSITIVE.search(name):
            raise ValueError("timing stage is invalid")
        canonical[name] = _optional_nonnegative_int(duration, "timing duration")
    state = "partial" if any(item is None for item in canonical.values()) else "known"
    return {"state": state, "value": canonical}


def _known(value: Any) -> dict[str, Any]:
    return {"state": "unknown" if value is None else "known", "value": value}


def _optional_ids(values: Sequence[str] | None, namespace: str, label: str) -> list[str] | None:
    if values is None:
        return None
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise ValueError(f"{label} IDs must be a sequence")
    canonical = sorted(set(values))
    for value in canonical:
        _require_id(value, {namespace}, label)
    return canonical


def _require_rows(rows: Sequence[Mapping[str, Any]], label: str) -> Sequence[Mapping[str, Any]]:
    if isinstance(rows, (str, bytes)) or not isinstance(rows, Sequence):
        raise ValueError(f"{label} rows must be a sequence")
    if any(not isinstance(row, Mapping) for row in rows):
        raise ValueError(f"{label} row must be a mapping")
    return rows


def _require_id(value: Any, namespaces: set[str], label: str) -> None:
    if not isinstance(value, str) or _ID.fullmatch(value) is None:
        raise ValueError(f"{label} identity must be a pseudonymous namespaced ID")
    if value.split(":", 1)[0] not in namespaces:
        raise ValueError(f"{label} identity must be a pseudonymous namespaced ID")


def _optional_text(value: str | None, label: str, *, maximum: int) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value or len(value.encode("utf-8")) > maximum or _SENSITIVE.search(value):
        raise ValueError(f"{label} is invalid or contains sensitive material")
    return value


def _optional_pattern(value: str | None, pattern: re.Pattern[str], label: str) -> str | None:
    if value is not None and (not isinstance(value, str) or pattern.fullmatch(value) is None):
        raise ValueError(f"{label} is invalid")
    return value


def _optional_count(value: int | None, label: str) -> int | None:
    return _optional_nonnegative_int(value, label)


def _optional_nonnegative_int(value: Any, label: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{label} must be a non-negative integer or null")
    return value


def _optional_positive_int(value: Any, label: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{label} must be a positive integer or null")
    return value


__all__ = ["build_engine_comparison_from_completed_state", "build_engine_comparison_record"]
