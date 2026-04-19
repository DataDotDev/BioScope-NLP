from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import json
from typing import Any

from bioscope_workers.contracts.schema import CONTRACT_SCHEMA_VERSION, INGESTION_EVENT_REQUIRED_FIELDS

ENRICHMENT_SCHEMA_VERSION = "1.0.0"


class ValidationError(ValueError):
    pass


def canonical_payload(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def compute_idempotency_key(envelope: dict[str, Any]) -> str:
    canonical = canonical_payload(
        {
            "schema_version": envelope.get("schema_version"),
            "source": envelope.get("source"),
            "record_type": envelope.get("record_type"),
            "observed_at": envelope.get("observed_at"),
            "ingested_at": envelope.get("ingested_at"),
            "normalized": envelope.get("normalized"),
            "raw": envelope.get("raw"),
            "identifiers": envelope.get("identifiers"),
        }
    )
    return sha256(canonical.encode("utf-8")).hexdigest()


@dataclass(slots=True)
class EventEnvelope:
    schema_version: str
    source: str
    record_type: str
    observed_at: str
    ingested_at: str
    normalized: dict[str, Any]
    raw: dict[str, Any]
    identifiers: dict[str, Any]
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = {
            "schema_version": self.schema_version,
            "source": self.source,
            "record_type": self.record_type,
            "observed_at": self.observed_at,
            "ingested_at": self.ingested_at,
            "normalized": self.normalized,
            "raw": self.raw,
            "identifiers": self.identifiers,
        }
        data.update(self.extra)
        return data


def _require_str(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{key} must be a non-empty string")
    return value


def _require_dict(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise ValidationError(f"{key} must be an object")
    return value


def load_envelope(payload: dict[str, Any]) -> EventEnvelope:
    if not isinstance(payload, dict):
        raise ValidationError("event payload must be an object")

    schema_version = _require_str(payload, "schema_version")
    if schema_version.split(".", 1)[0] != CONTRACT_SCHEMA_VERSION.split(".", 1)[0]:
        raise ValidationError(
            f"unsupported schema_version {schema_version}; expected major version {CONTRACT_SCHEMA_VERSION}"
        )

    required = set(INGESTION_EVENT_REQUIRED_FIELDS) - {"schema_version"}
    missing = sorted(required - payload.keys())
    if missing:
        raise ValidationError(f"missing required fields: {', '.join(missing)}")

    known_keys = set(INGESTION_EVENT_REQUIRED_FIELDS)
    extra = {key: value for key, value in payload.items() if key not in known_keys}

    return EventEnvelope(
        schema_version=schema_version,
        source=_require_str(payload, "source"),
        record_type=_require_str(payload, "record_type"),
        observed_at=_require_str(payload, "observed_at"),
        ingested_at=_require_str(payload, "ingested_at"),
        normalized=_require_dict(payload, "normalized"),
        raw=_require_dict(payload, "raw"),
        identifiers=_require_dict(payload, "identifiers"),
        extra=extra,
    )
