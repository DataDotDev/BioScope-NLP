from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

CONTRACT_SCHEMA_VERSION = "1.0.0"
ENRICHMENT_SCHEMA_VERSION = "1.0.0"

INGESTION_EVENT_SCHEMA_NAME = "bioscope.ingestion.event"
ENRICHED_EVENT_SCHEMA_NAME = "bioscope.enrichment.event"

INGESTION_EVENT_REQUIRED_FIELDS = (
    "schema_version",
    "source",
    "record_type",
    "observed_at",
    "ingested_at",
    "normalized",
    "raw",
    "identifiers",
)

ENRICHED_EVENT_REQUIRED_FIELDS = (
    "transport",
    "idempotency_key",
    "enrichment_schema_version",
    "input_event",
    "entities",
    "classifications",
    "alerts",
    "enriched_at",
)


@dataclass(frozen=True, slots=True)
class SharedSchema:
    name: str
    version: str
    required_fields: tuple[str, ...]
    description: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "required_fields": list(self.required_fields),
        }


INGESTION_EVENT_SCHEMA = SharedSchema(
    name=INGESTION_EVENT_SCHEMA_NAME,
    version=CONTRACT_SCHEMA_VERSION,
    required_fields=INGESTION_EVENT_REQUIRED_FIELDS,
    description="Canonical ingestion envelope shared by the ingestion and NLP worker repositories.",
)

ENRICHED_EVENT_SCHEMA = SharedSchema(
    name=ENRICHED_EVENT_SCHEMA_NAME,
    version=ENRICHMENT_SCHEMA_VERSION,
    required_fields=ENRICHED_EVENT_REQUIRED_FIELDS,
    description="Enriched worker output contract consumed by downstream storage and backend services.",
)


def schema_bundle() -> dict[str, Any]:
    return {
        "bundle_name": "bioscope.shared.contracts",
        "bundle_version": CONTRACT_SCHEMA_VERSION,
        "schemas": [INGESTION_EVENT_SCHEMA.to_dict(), ENRICHED_EVENT_SCHEMA.to_dict()],
    }


def export_schema_bundle(path: str | Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(schema_bundle(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def load_schema_bundle(path: str | Path) -> dict[str, Any]:
    raw_bundle = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw_bundle, dict):
        raise ValueError("schema bundle must be a JSON object")
    return raw_bundle
