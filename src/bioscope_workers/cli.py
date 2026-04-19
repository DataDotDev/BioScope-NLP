from __future__ import annotations

import argparse
import logging
import time
from pathlib import Path

from bioscope_workers.config import RuntimeSettings
from bioscope_workers.contracts.envelope import CONTRACT_SCHEMA_VERSION
from bioscope_workers.runtime.file_watch import read_new_jsonl_records
from bioscope_workers.runtime.state import FileCheckpointStore, FileCursorStore, MemoryCheckpointStore, MemoryCursorStore
from bioscope_workers.runtime.worker import WorkerPipeline
from bioscope_workers.transports.jsonl import JsonlReader, JsonlWriter


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="BioScope NLP worker service")
    parser.add_argument("--mode", choices=("replay", "watch"), required=True)
    parser.add_argument("--input", help="JSONL input file")
    parser.add_argument("--output", help="JSONL output file")
    parser.add_argument("--checkpoint", help="Optional checkpoint file for idempotency")
    parser.add_argument("--cursor-file", help="Optional cursor file for watch mode")
    parser.add_argument("--poll-interval-seconds", type=float, help="Watch mode poll interval")
    parser.add_argument("--idle-log-interval-seconds", type=float, help="Watch mode idle logging interval")
    parser.add_argument("--log-level", help="Log level (env: BIOSCOPE_LOG_LEVEL)")
    return parser


def normalize_replay_payload(payload: dict) -> dict:
    normalized_payload = dict(payload)
    normalized_payload.setdefault("schema_version", CONTRACT_SCHEMA_VERSION)
    return normalized_payload


def _run_replay(input_path: str, output_path: str, checkpoint_path: str | None, pipeline: WorkerPipeline) -> int:
    reader = JsonlReader(input_path)
    writer = JsonlWriter(output_path)
    processed_count = 0
    for payload in reader.read():
        processed = pipeline.process(normalize_replay_payload(payload), transport="replay")
        if processed is not None:
            writer.write(processed.to_dict())
            processed_count += 1
    return processed_count


def _run_watch(
    input_path: str,
    output_path: str,
    cursor_path: str,
    poll_interval_seconds: float,
    idle_log_interval_seconds: float,
    pipeline: WorkerPipeline,
    logger: logging.Logger,
) -> int:
    writer = JsonlWriter(output_path)
    cursor_store = FileCursorStore(cursor_path)
    position = cursor_store.load()
    last_idle_log = time.monotonic()
    processed_count = 0

    while True:
        records, next_position = read_new_jsonl_records(input_path, position)
        if records:
            for payload in records:
                processed = pipeline.process(normalize_replay_payload(payload), transport="watch")
                if processed is not None:
                    writer.write(processed.to_dict())
                    processed_count += 1
            position = next_position
            cursor_store.save(position)
            continue

        if not Path(input_path).exists():
            if time.monotonic() - last_idle_log >= idle_log_interval_seconds:
                logger.info("watching_for_input input=%s output=%s", input_path, output_path)
                last_idle_log = time.monotonic()
        elif time.monotonic() - last_idle_log >= idle_log_interval_seconds:
            logger.info("watching_for_new_records input=%s output=%s offset=%d", input_path, output_path, position)
            last_idle_log = time.monotonic()

        time.sleep(poll_interval_seconds)

    return processed_count


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    settings = RuntimeSettings.from_env()

    log_level = args.log_level or settings.log_level
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logger = logging.getLogger("bioscope_workers")

    checkpoint_store = FileCheckpointStore(args.checkpoint) if args.checkpoint else MemoryCheckpointStore()
    pipeline = WorkerPipeline(checkpoint_store=checkpoint_store, logger=logger)

    if args.mode == "replay":
        input_path = args.input or settings.replay_input
        output_path = args.output or settings.replay_output
        checkpoint_path = args.checkpoint or settings.replay_checkpoint
        if not input_path or not output_path:
            parser.error("--input and --output are required in replay mode")
        logger.info("starting replay input=%s output=%s checkpoint=%s", input_path, output_path, checkpoint_path)
        processed_count = _run_replay(input_path, output_path, checkpoint_path, pipeline)
        logger.info("run_summary mode=replay processed=%d", processed_count)
        return 0

    input_path = args.input or settings.watch_input_file
    output_path = args.output or settings.watch_output_file
    cursor_path = args.cursor_file or settings.watch_cursor_file
    poll_interval_seconds = (
        args.poll_interval_seconds if args.poll_interval_seconds is not None else settings.watch_poll_interval_seconds
    )
    idle_log_interval_seconds = (
        args.idle_log_interval_seconds
        if args.idle_log_interval_seconds is not None
        else settings.watch_idle_log_interval_seconds
    )
    if not input_path or not output_path:
        parser.error("--input and --output are required in watch mode")

    logger.info(
        "starting watch mode input=%s output=%s cursor=%s poll_interval_seconds=%s",
        input_path,
        output_path,
        cursor_path,
        poll_interval_seconds,
    )
    try:
        _run_watch(
            input_path=input_path,
            output_path=output_path,
            cursor_path=cursor_path,
            poll_interval_seconds=poll_interval_seconds,
            idle_log_interval_seconds=idle_log_interval_seconds,
            pipeline=pipeline,
            logger=logger,
        )
    except KeyboardInterrupt:
        logger.info("shutdown_requested signal=KeyboardInterrupt")
        return 0

    return 0
