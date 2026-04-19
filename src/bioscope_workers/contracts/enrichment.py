from __future__ import annotations

from typing import Any

from bioscope_workers.contracts.envelope import ENRICHMENT_SCHEMA_VERSION, ValidationError


def validate_enriched_event(payload: dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise ValidationError("enriched payload must be an object")

    required = {
        "transport",
        "idempotency_key",
        "enrichment_schema_version",
        "input_event",
        "entities",
        "classifications",
        "alerts",
        "enriched_at",
    }
    missing = sorted(required - payload.keys())
    if missing:
        raise ValidationError(f"enriched payload missing required fields: {', '.join(missing)}")

    if payload.get("enrichment_schema_version") != ENRICHMENT_SCHEMA_VERSION:
        raise ValidationError(
            "enrichment_schema_version mismatch: "
            f"{payload.get('enrichment_schema_version')} != {ENRICHMENT_SCHEMA_VERSION}"
        )

    str_fields = ("transport", "idempotency_key", "enriched_at")
    for field in str_fields:
        value = payload.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValidationError(f"{field} must be a non-empty string")

    dict_fields = ("input_event", "entities", "classifications", "alerts")
    for field in dict_fields:
        if not isinstance(payload.get(field), dict):
            raise ValidationError(f"{field} must be an object")
