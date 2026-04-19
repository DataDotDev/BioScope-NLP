import json
import shutil

import pytest

from bioscope_workers.runtime.worker import WorkerPipeline
from bioscope_workers.transports.kafka import KafkaEnvelopeSink, KafkaEnvelopeSource, KafkaSettings


def sample_payload() -> dict:
    return {
        "schema_version": "1.0.0",
        "source": "EMA RSS",
        "record_type": "regulatory_update",
        "observed_at": "2026-04-19T12:00:00Z",
        "ingested_at": "2026-04-19T12:00:03Z",
        "normalized": {
            "title": "EMA warning for XYZ-22 in partnership with Beta Labs",
            "company": "Beta Labs Ltd.",
            "drug": "XYZ-22",
            "phase": "Phase I",
        },
        "raw": {"title": "EMA warning for XYZ-22 in partnership with Beta Labs"},
        "identifiers": {"url": "https://example.test/ema"},
    }


@pytest.mark.integration
def test_kafka_roundtrip_with_real_broker() -> None:
    if shutil.which("docker") is None:
        pytest.skip("docker is required for Kafka integration tests")

    kafka_module = pytest.importorskip("kafka")
    testcontainers_kafka = pytest.importorskip("testcontainers.kafka")

    KafkaContainer = testcontainers_kafka.KafkaContainer
    KafkaProducer = kafka_module.KafkaProducer
    KafkaConsumer = kafka_module.KafkaConsumer

    with KafkaContainer() as kafka_container:
        bootstrap_servers = kafka_container.get_bootstrap_server()
        input_topic = "bioscope.ingestion.events"
        output_topic = "bioscope.enrichment.processed"

        producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            value_serializer=lambda value: json.dumps(value).encode("utf-8"),
        )
        producer.send(input_topic, sample_payload()).get(timeout=30)
        producer.flush()
        producer.close()

        settings = KafkaSettings(
            bootstrap_servers=bootstrap_servers,
            input_topic=input_topic,
            output_topic=output_topic,
            group_id="bioscope-nlp-workers-integration",
            consumer_timeout_ms=5000,
        )

        source = KafkaEnvelopeSource(settings)
        source_iter = iter(source.read())
        ingested_payload = next(source_iter)

        processed = WorkerPipeline().process(ingested_payload, transport="kafka")
        assert processed is not None

        sink = KafkaEnvelopeSink(settings)
        sink.write(processed.to_dict())
        sink.close()

        consumer = KafkaConsumer(
            output_topic,
            bootstrap_servers=bootstrap_servers,
            auto_offset_reset="earliest",
            enable_auto_commit=False,
            consumer_timeout_ms=5000,
            value_deserializer=lambda value: json.loads(value.decode("utf-8")),
        )
        messages = [message.value for message in consumer]
        consumer.close()

        assert messages
        assert messages[0]["idempotency_key"] == processed.idempotency_key
        assert messages[0]["entities"] == processed.entities
