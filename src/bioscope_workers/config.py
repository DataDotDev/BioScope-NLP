from __future__ import annotations

from dataclasses import dataclass
import os


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    return int(value)


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    return float(value)


@dataclass(slots=True)
class AppSettings:
    log_level: str = "INFO"
    bootstrap_servers: str | None = None
    input_topic: str | None = None
    output_topic: str = "bioscope.enrichment.processed"
    group_id: str = "bioscope-nlp-workers"
    kafka_max_retries: int = 3
    kafka_retry_backoff_seconds: float = 1.0
    kafka_producer_timeout_seconds: int = 30
    kafka_consumer_timeout_ms: int | None = None
    dlq_path: str | None = None

    @classmethod
    def from_env(cls) -> AppSettings:
        consumer_timeout_raw = os.getenv("BIOSCOPE_KAFKA_CONSUMER_TIMEOUT_MS")
        consumer_timeout = int(consumer_timeout_raw) if consumer_timeout_raw else None
        return cls(
            log_level=os.getenv("BIOSCOPE_LOG_LEVEL", "INFO"),
            bootstrap_servers=os.getenv("BIOSCOPE_KAFKA_BOOTSTRAP_SERVERS"),
            input_topic=os.getenv("BIOSCOPE_KAFKA_INPUT_TOPIC"),
            output_topic=os.getenv("BIOSCOPE_KAFKA_OUTPUT_TOPIC", "bioscope.enrichment.processed"),
            group_id=os.getenv("BIOSCOPE_KAFKA_GROUP_ID", "bioscope-nlp-workers"),
            kafka_max_retries=_env_int("BIOSCOPE_KAFKA_MAX_RETRIES", 3),
            kafka_retry_backoff_seconds=_env_float("BIOSCOPE_KAFKA_RETRY_BACKOFF_SECONDS", 1.0),
            kafka_producer_timeout_seconds=_env_int("BIOSCOPE_KAFKA_PRODUCER_TIMEOUT_SECONDS", 30),
            kafka_consumer_timeout_ms=consumer_timeout,
            dlq_path=os.getenv("BIOSCOPE_KAFKA_DLQ_PATH"),
        )
