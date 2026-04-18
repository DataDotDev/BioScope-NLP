import json

from bioscope_workers.cli import normalize_replay_payload
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


def test_replay_payload_backfills_schema_version() -> None:
    legacy_payload = {
        "source": "clinicaltrials.gov",
        "record_type": "clinical_trial",
        "observed_at": "2026-04-12T18:30:00Z",
        "ingested_at": "2026-04-14T05:48:22.376460Z",
        "normalized": {"title": "Legacy replay payload"},
        "raw": {"title": "Legacy replay payload"},
        "identifiers": {"nct_id": "NCT07525791"},
    }

    normalized_payload = normalize_replay_payload(legacy_payload)

    assert normalized_payload["schema_version"] == "1.0.0"
    assert normalized_payload["source"] == "clinicaltrials.gov"
