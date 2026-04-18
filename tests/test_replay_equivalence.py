import json

from bioscope_workers.runtime.worker import WorkerPipeline
from bioscope_workers.transports.jsonl import JsonlReader


def sample_payload() -> dict:
    return {
        "schema_version": "1.0.0",
        "source": "EMA RSS",
        "record_type": "regulatory_update",
        "observed_at": "2026-04-18T12:00:00Z",
        "ingested_at": "2026-04-18T12:00:03Z",
        "normalized": {
            "title": "EMA warning for XYZ-22 in partnership with Beta Labs",
            "company": "Beta Labs Ltd.",
            "drug": "XYZ-22",
            "phase": "Phase I",
        },
        "raw": {"title": "EMA warning for XYZ-22 in partnership with Beta Labs"},
        "identifiers": {"url": "https://example.test/ema"},
    }


def test_jsonl_replay_matches_direct_processing(tmp_path) -> None:
    input_path = tmp_path / "events.jsonl"
    input_path.write_text(json.dumps(sample_payload()) + "\n", encoding="utf-8")

    pipeline = WorkerPipeline()
    replay_events = []
    for payload in JsonlReader(input_path).read():
        processed = pipeline.process(payload, transport="jsonl")
        assert processed is not None
        replay_events.append(processed.to_dict())

    direct = WorkerPipeline().process(sample_payload(), transport="kafka")
    assert direct is not None

    assert replay_events[0]["entities"] == direct.entities
    assert replay_events[0]["classifications"] == direct.classifications
