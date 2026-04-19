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
class RuntimeSettings:
    log_level: str = "INFO"
    replay_input: str | None = None
    replay_output: str = "examples/enriched-events.jsonl"
    replay_checkpoint: str = "examples/replay.checkpoints"
    watch_input_file: str | None = None
    watch_output_file: str = "examples/enriched-stream.jsonl"
    watch_cursor_file: str = "examples/stream.cursor"
    watch_poll_interval_seconds: float = 2.0
    watch_idle_log_interval_seconds: float = 30.0

    @classmethod
    def from_env(cls) -> RuntimeSettings:
        return cls(
            log_level=os.getenv("BIOSCOPE_LOG_LEVEL", "INFO"),
            replay_input=os.getenv("BIOSCOPE_REPLAY_INPUT"),
            replay_output=os.getenv("BIOSCOPE_REPLAY_OUTPUT", "examples/enriched-events.jsonl"),
            replay_checkpoint=os.getenv("BIOSCOPE_REPLAY_CHECKPOINT", "examples/replay.checkpoints"),
            watch_input_file=os.getenv("BIOSCOPE_WATCH_INPUT_FILE"),
            watch_output_file=os.getenv("BIOSCOPE_WATCH_OUTPUT_FILE", "examples/enriched-stream.jsonl"),
            watch_cursor_file=os.getenv("BIOSCOPE_WATCH_CURSOR_FILE", "examples/stream.cursor"),
            watch_poll_interval_seconds=_env_float("BIOSCOPE_WATCH_POLL_INTERVAL_SECONDS", 2.0),
            watch_idle_log_interval_seconds=_env_float("BIOSCOPE_WATCH_IDLE_LOG_INTERVAL_SECONDS", 30.0),
        )
