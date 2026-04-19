from bioscope_workers.config import RuntimeSettings


def test_runtime_settings_reads_file_env(monkeypatch) -> None:
    monkeypatch.setenv("BIOSCOPE_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("BIOSCOPE_REPLAY_INPUT", "input.jsonl")
    monkeypatch.setenv("BIOSCOPE_REPLAY_OUTPUT", "output.jsonl")
    monkeypatch.setenv("BIOSCOPE_REPLAY_CHECKPOINT", "replay.checkpoints")
    monkeypatch.setenv("BIOSCOPE_WATCH_INPUT_FILE", "handoff/ingestion.jsonl")
    monkeypatch.setenv("BIOSCOPE_WATCH_OUTPUT_FILE", "handoff/enriched.jsonl")
    monkeypatch.setenv("BIOSCOPE_WATCH_CURSOR_FILE", "handoff/stream.cursor")
    monkeypatch.setenv("BIOSCOPE_WATCH_POLL_INTERVAL_SECONDS", "1.25")
    monkeypatch.setenv("BIOSCOPE_WATCH_IDLE_LOG_INTERVAL_SECONDS", "15")

    settings = RuntimeSettings.from_env()

    assert settings.log_level == "DEBUG"
    assert settings.replay_input == "input.jsonl"
    assert settings.replay_output == "output.jsonl"
    assert settings.replay_checkpoint == "replay.checkpoints"
    assert settings.watch_input_file == "handoff/ingestion.jsonl"
    assert settings.watch_output_file == "handoff/enriched.jsonl"
    assert settings.watch_cursor_file == "handoff/stream.cursor"
    assert settings.watch_poll_interval_seconds == 1.25
    assert settings.watch_idle_log_interval_seconds == 15.0


def test_runtime_settings_defaults_when_env_missing(monkeypatch) -> None:
    for key in (
        "BIOSCOPE_LOG_LEVEL",
        "BIOSCOPE_REPLAY_INPUT",
        "BIOSCOPE_REPLAY_OUTPUT",
        "BIOSCOPE_REPLAY_CHECKPOINT",
        "BIOSCOPE_WATCH_INPUT_FILE",
        "BIOSCOPE_WATCH_OUTPUT_FILE",
        "BIOSCOPE_WATCH_CURSOR_FILE",
        "BIOSCOPE_WATCH_POLL_INTERVAL_SECONDS",
        "BIOSCOPE_WATCH_IDLE_LOG_INTERVAL_SECONDS",
    ):
        monkeypatch.delenv(key, raising=False)

    settings = RuntimeSettings.from_env()

    assert settings.log_level == "INFO"
    assert settings.replay_input is None
    assert settings.replay_output == "examples/enriched-events.jsonl"
    assert settings.replay_checkpoint == "examples/replay.checkpoints"
    assert settings.watch_input_file is None
    assert settings.watch_output_file == "examples/enriched-stream.jsonl"
    assert settings.watch_cursor_file == "examples/stream.cursor"
    assert settings.watch_poll_interval_seconds == 2.0
    assert settings.watch_idle_log_interval_seconds == 30.0
