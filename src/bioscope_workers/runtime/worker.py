from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import logging
from typing import Any

from bioscope_workers.contracts.enrichment import validate_enriched_event
from bioscope_workers.contracts.envelope import ENRICHMENT_SCHEMA_VERSION, compute_idempotency_key, load_envelope
from bioscope_workers.runtime.state import CheckpointStore
from bioscope_workers.services.alerts import AlertService
from bioscope_workers.services.classifier import ClassifierService
from bioscope_workers.services.entity import EntityService


@dataclass(slots=True)
class ProcessedEvent:
    transport: str
    idempotency_key: str
    enrichment_schema_version: str
    input_event: dict[str, Any]
    entities: dict[str, Any]
    classifications: dict[str, Any]
    alerts: dict[str, Any]
    enriched_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "transport": self.transport,
            "idempotency_key": self.idempotency_key,
            "enrichment_schema_version": self.enrichment_schema_version,
            "input_event": self.input_event,
            "entities": self.entities,
            "classifications": self.classifications,
            "alerts": self.alerts,
            "enriched_at": self.enriched_at,
        }


class WorkerPipeline:
    def __init__(
        self,
        entity_service: EntityService | None = None,
        classifier_service: ClassifierService | None = None,
        alert_service: AlertService | None = None,
        checkpoint_store: CheckpointStore | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        self.entity_service = entity_service or EntityService()
        self.classifier_service = classifier_service or ClassifierService()
        self.alert_service = alert_service or AlertService()
        self.checkpoint_store = checkpoint_store
        self.logger = logger or logging.getLogger("bioscope_workers")

    def process(self, payload: dict[str, Any], transport: str) -> ProcessedEvent | None:
        envelope = load_envelope(payload)
        envelope_dict = envelope.to_dict()
        idempotency_key = compute_idempotency_key(envelope_dict)

        if self.checkpoint_store and self.checkpoint_store.seen(idempotency_key):
            self.logger.info("duplicate event skipped", extra={"idempotency_key": idempotency_key, "transport": transport})
            return None

        entities = self.entity_service.extract(envelope_dict).to_dict()
        classifications = self.classifier_service.classify(envelope_dict, entities).to_dict()
        alerts = self.alert_service.maybe_emit(envelope_dict, classifications, entities).to_dict()

        processed = ProcessedEvent(
            transport=transport,
            idempotency_key=idempotency_key,
            enrichment_schema_version=ENRICHMENT_SCHEMA_VERSION,
            input_event=envelope_dict,
            entities=entities,
            classifications=classifications,
            alerts=alerts,
            enriched_at=datetime.now(timezone.utc).isoformat(),
        )

        validate_enriched_event(processed.to_dict())

        if self.checkpoint_store:
            self.checkpoint_store.mark(idempotency_key)

        return processed
