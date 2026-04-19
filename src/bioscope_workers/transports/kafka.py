from __future__ import annotations

from dataclasses import dataclass
import json
import time
from typing import Any, Iterable


@dataclass(slots=True)
class KafkaSettings:
    bootstrap_servers: str
    input_topic: str
    output_topic: str
    group_id: str
    max_retries: int = 3
    retry_backoff_seconds: float = 1.0
    producer_timeout_seconds: int = 30
    consumer_timeout_ms: int | None = None


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
            consumer_timeout_ms=self.settings.consumer_timeout_ms,
            value_deserializer=lambda value: json.loads(value.decode("utf-8")),
        )
        try:
            for message in consumer:
                yield message.value
        finally:
            consumer.close()


class KafkaEnvelopeSink:
    def __init__(self, settings: KafkaSettings) -> None:
        self.settings = settings
        try:
            from kafka import KafkaProducer  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise RuntimeError("Kafka mode requires the kafka-python package. Install with pip install -e .[kafka].") from exc

        self._producer = KafkaProducer(
            bootstrap_servers=self.settings.bootstrap_servers,
            value_serializer=lambda value: json.dumps(value, sort_keys=True).encode("utf-8"),
        )

    def write(self, payload: dict[str, Any]) -> None:
        attempt = 0
        while True:
            try:
                future = self._producer.send(self.settings.output_topic, payload)
                future.get(timeout=self.settings.producer_timeout_seconds)
                self._producer.flush()
                return
            except Exception:
                if attempt >= self.settings.max_retries:
                    raise
                backoff = self.settings.retry_backoff_seconds * (2**attempt)
                time.sleep(backoff)
                attempt += 1

    def close(self) -> None:
        self._producer.close()
