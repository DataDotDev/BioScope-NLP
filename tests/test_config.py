import os

from bioscope_workers.config import AppSettings


def test_app_settings_reads_kafka_env(monkeypatch) -> None:
    monkeypatch.setenv("BIOSCOPE_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("BIOSCOPE_KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    monkeypatch.setenv("BIOSCOPE_KAFKA_INPUT_TOPIC", "bioscope.ingestion.events")
    monkeypatch.setenv("BIOSCOPE_KAFKA_OUTPUT_TOPIC", "bioscope.enrichment.processed")
    monkeypatch.setenv("BIOSCOPE_KAFKA_GROUP_ID", "bioscope-workers")
    monkeypatch.setenv("BIOSCOPE_KAFKA_MAX_RETRIES", "5")
    monkeypatch.setenv("BIOSCOPE_KAFKA_RETRY_BACKOFF_SECONDS", "1.5")
    monkeypatch.setenv("BIOSCOPE_KAFKA_PRODUCER_TIMEOUT_SECONDS", "45")
    monkeypatch.setenv("BIOSCOPE_KAFKA_CONSUMER_TIMEOUT_MS", "1000")
    monkeypatch.setenv("BIOSCOPE_KAFKA_DLQ_PATH", "examples/dlq.jsonl")

    settings = AppSettings.from_env()

    assert settings.log_level == "DEBUG"
    assert settings.bootstrap_servers == "localhost:9092"
    assert settings.input_topic == "bioscope.ingestion.events"
    assert settings.output_topic == "bioscope.enrichment.processed"
    assert settings.group_id == "bioscope-workers"
    assert settings.kafka_max_retries == 5
    assert settings.kafka_retry_backoff_seconds == 1.5
    assert settings.kafka_producer_timeout_seconds == 45
    assert settings.kafka_consumer_timeout_ms == 1000
    assert settings.dlq_path == "examples/dlq.jsonl"


def test_app_settings_defaults_when_env_missing(monkeypatch) -> None:
    for key in list(os.environ):
        if key.startswith("BIOSCOPE_"):
            monkeypatch.delenv(key, raising=False)

    settings = AppSettings.from_env()

    assert settings.log_level == "INFO"
    assert settings.bootstrap_servers is None
    assert settings.input_topic is None
    assert settings.output_topic == "bioscope.enrichment.processed"
    assert settings.group_id == "bioscope-nlp-workers"
    assert settings.kafka_max_retries == 3
    assert settings.kafka_retry_backoff_seconds == 1.0
    assert settings.kafka_producer_timeout_seconds == 30
    assert settings.kafka_consumer_timeout_ms is None
    assert settings.dlq_path is None
