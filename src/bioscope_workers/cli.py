from __future__ import annotations

import argparse
import logging
from pathlib import Path

from bioscope_workers.config import AppSettings
from bioscope_workers.contracts.envelope import CONTRACT_SCHEMA_VERSION
from bioscope_workers.runtime.state import FileCheckpointStore, MemoryCheckpointStore
from bioscope_workers.runtime.worker import WorkerPipeline
from bioscope_workers.transports.jsonl import JsonlReader, JsonlWriter


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="BioScope NLP worker service")
    parser.add_argument("--mode", choices=("replay", "kafka"), required=True)
    parser.add_argument("--input", help="JSONL input file for replay mode")
    parser.add_argument("--output", help="JSONL output file for replay mode")
    parser.add_argument("--bootstrap-servers", help="Kafka bootstrap servers (env: BIOSCOPE_KAFKA_BOOTSTRAP_SERVERS)")
    parser.add_argument("--input-topic", help="Kafka topic for ingestion events (env: BIOSCOPE_KAFKA_INPUT_TOPIC)")
    parser.add_argument("--output-topic", help="Kafka topic for enriched events (env: BIOSCOPE_KAFKA_OUTPUT_TOPIC)")
    parser.add_argument("--group-id", help="Kafka consumer group id (env: BIOSCOPE_KAFKA_GROUP_ID)")
    parser.add_argument("--max-retries", type=int, help="Kafka producer retries (env: BIOSCOPE_KAFKA_MAX_RETRIES)")
    parser.add_argument(
        "--retry-backoff-seconds",
        type=float,
        help="Kafka producer retry backoff in seconds (env: BIOSCOPE_KAFKA_RETRY_BACKOFF_SECONDS)",
    )
    parser.add_argument(
        "--producer-timeout-seconds",
        type=int,
        help="Kafka producer send timeout in seconds (env: BIOSCOPE_KAFKA_PRODUCER_TIMEOUT_SECONDS)",
    )
    parser.add_argument(
        "--consumer-timeout-ms",
        type=int,
        help="Kafka consumer timeout in ms (env: BIOSCOPE_KAFKA_CONSUMER_TIMEOUT_MS)",
    )
    parser.add_argument("--dlq-path", help="Local JSONL dead-letter output path (env: BIOSCOPE_KAFKA_DLQ_PATH)")
    parser.add_argument("--checkpoint", help="Optional checkpoint file for idempotency")
    parser.add_argument("--log-level", help="Log level (env: BIOSCOPE_LOG_LEVEL)")
    return parser


def normalize_replay_payload(payload: dict) -> dict:
    normalized_payload = dict(payload)
    normalized_payload.setdefault("schema_version", CONTRACT_SCHEMA_VERSION)
    return normalized_payload


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    settings = AppSettings.from_env()

    log_level = args.log_level or settings.log_level

    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logger = logging.getLogger("bioscope_workers")

    checkpoint_store = FileCheckpointStore(args.checkpoint) if args.checkpoint else MemoryCheckpointStore()
    pipeline = WorkerPipeline(checkpoint_store=checkpoint_store, logger=logger)

    if args.mode == "replay":
        if not args.input or not args.output:
            parser.error("--input and --output are required in replay mode")
        reader = JsonlReader(args.input)
        writer = JsonlWriter(args.output)
        for payload in reader.read():
            processed = pipeline.process(normalize_replay_payload(payload), transport="jsonl")
            if processed is not None:
                writer.write(processed.to_dict())
        return 0

    bootstrap_servers = args.bootstrap_servers or settings.bootstrap_servers
    input_topic = args.input_topic or settings.input_topic
    output_topic = args.output_topic or settings.output_topic
    group_id = args.group_id or settings.group_id
    max_retries = args.max_retries if args.max_retries is not None else settings.kafka_max_retries
    retry_backoff = (
        args.retry_backoff_seconds
        if args.retry_backoff_seconds is not None
        else settings.kafka_retry_backoff_seconds
    )
    producer_timeout = (
        args.producer_timeout_seconds
        if args.producer_timeout_seconds is not None
        else settings.kafka_producer_timeout_seconds
    )
    consumer_timeout = (
        args.consumer_timeout_ms if args.consumer_timeout_ms is not None else settings.kafka_consumer_timeout_ms
    )
    dlq_path = args.dlq_path or settings.dlq_path

    if not bootstrap_servers or not input_topic:
        parser.error("--bootstrap-servers and --input-topic are required in kafka mode")

    from bioscope_workers.transports.kafka import KafkaEnvelopeSink, KafkaEnvelopeSource, KafkaSettings

    settings = KafkaSettings(
        bootstrap_servers=bootstrap_servers,
        input_topic=input_topic,
        output_topic=output_topic,
        group_id=group_id,
        max_retries=max_retries,
        retry_backoff_seconds=retry_backoff,
        producer_timeout_seconds=producer_timeout,
        consumer_timeout_ms=consumer_timeout,
    )
    source = KafkaEnvelopeSource(settings)
    sink = KafkaEnvelopeSink(settings)
    dlq_writer = JsonlWriter(Path(dlq_path)) if dlq_path else None
    counters = {"received": 0, "processed": 0, "duplicates": 0, "failed": 0, "dlq": 0}

    try:
        for payload in source.read():
            counters["received"] += 1
            try:
                processed = pipeline.process(payload, transport="kafka")
                if processed is None:
                    counters["duplicates"] += 1
                    continue
                sink.write(processed.to_dict())
                counters["processed"] += 1
                logger.info(
                    "event_processed source=%s record_type=%s idempotency_key=%s",
                    processed.input_event.get("source", ""),
                    processed.input_event.get("record_type", ""),
                    processed.idempotency_key,
                )
            except Exception as exc:
                counters["failed"] += 1
                logger.exception("event_failed error=%s", exc)
                if dlq_writer:
                    dlq_writer.write(
                        {
                            "reason": str(exc),
                            "payload": payload,
                        }
                    )
                    counters["dlq"] += 1
                else:
                    raise
    except KeyboardInterrupt:
        logger.info("shutdown_requested signal=KeyboardInterrupt")
    finally:
        sink.close()
        logger.info(
            "run_summary transport=kafka received=%d processed=%d duplicates=%d failed=%d dlq=%d",
            counters["received"],
            counters["processed"],
            counters["duplicates"],
            counters["failed"],
            counters["dlq"],
        )

    return 0
