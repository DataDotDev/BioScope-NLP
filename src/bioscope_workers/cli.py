from __future__ import annotations

import argparse
import logging

from bioscope_workers.contracts.envelope import CONTRACT_SCHEMA_VERSION
from bioscope_workers.runtime.state import FileCheckpointStore, MemoryCheckpointStore
from bioscope_workers.runtime.worker import WorkerPipeline
from bioscope_workers.transports.jsonl import JsonlReader, JsonlWriter


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="BioScope NLP worker service")
    parser.add_argument("--mode", choices=("replay", "kafka"), required=True)
    parser.add_argument("--input", help="JSONL input file for replay mode")
    parser.add_argument("--output", help="JSONL output file for replay mode")
    parser.add_argument("--bootstrap-servers", help="Kafka bootstrap servers")
    parser.add_argument("--input-topic", help="Kafka topic for ingestion events")
    parser.add_argument("--output-topic", default="bioscope.enrichment.processed", help="Kafka topic for enriched events")
    parser.add_argument("--group-id", default="bioscope-nlp-workers", help="Kafka consumer group id")
    parser.add_argument("--checkpoint", help="Optional checkpoint file for idempotency")
    parser.add_argument("--log-level", default="INFO")
    return parser


def normalize_replay_payload(payload: dict) -> dict:
    normalized_payload = dict(payload)
    normalized_payload.setdefault("schema_version", CONTRACT_SCHEMA_VERSION)
    return normalized_payload


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
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

    if not args.bootstrap_servers or not args.input_topic:
        parser.error("--bootstrap-servers and --input-topic are required in kafka mode")

    from bioscope_workers.transports.kafka import KafkaEnvelopeSink, KafkaEnvelopeSource, KafkaSettings

    settings = KafkaSettings(
        bootstrap_servers=args.bootstrap_servers,
        input_topic=args.input_topic,
        output_topic=args.output_topic,
        group_id=args.group_id,
    )
    source = KafkaEnvelopeSource(settings)
    sink = KafkaEnvelopeSink(settings)

    for payload in source.read():
        processed = pipeline.process(payload, transport="kafka")
        if processed is not None:
            sink.write(processed.to_dict())

    return 0
