from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Iterable


@dataclass(slots=True)
class KafkaSettings:
    bootstrap_servers: str
    input_topic: str
    output_topic: str
    group_id: str


class KafkaEnvelopeSource:
    def __init__(self, settings: KafkaSettings) -> None:
        self.settings = settings

    def read(self) -> Iterable[dict[str, Any]]:
        try:
            from kafka import KafkaConsumer  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("Kafka mode requires the kafka-python package. Install with pip install -e .[kafka].") from exc

        consumer = KafkaConsumer(
            self.settings.input_topic,
            bootstrap_servers=self.settings.bootstrap_servers,
            group_id=self.settings.group_id,
            enable_auto_commit=False,
            auto_offset_reset="earliest",
            value_deserializer=lambda value: json.loads(value.decode("utf-8")),
        )
        for message in consumer:
            yield message.value


class KafkaEnvelopeSink:
    def __init__(self, settings: KafkaSettings) -> None:
        self.settings = settings

    def write(self, payload: dict[str, Any]) -> None:
        try:
            from kafka import KafkaProducer  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("Kafka mode requires the kafka-python package. Install with pip install -e .[kafka].") from exc

        producer = KafkaProducer(
            bootstrap_servers=self.settings.bootstrap_servers,
            value_serializer=lambda value: json.dumps(value, sort_keys=True).encode("utf-8"),
        )
        future = producer.send(self.settings.output_topic, payload)
        future.get(timeout=30)
        producer.flush()
