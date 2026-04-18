from bioscope_workers.runtime.state import MemoryCheckpointStore
from bioscope_workers.runtime.worker import WorkerPipeline


def sample_payload() -> dict:
    return {
        "schema_version": "1.0.0",
        "source": "FDA openFDA JSON",
        "record_type": "label_change",
        "observed_at": "2026-04-18T11:00:00Z",
        "ingested_at": "2026-04-18T11:00:08Z",
        "normalized": {
            "title": "FDA label change for ACME Pharma's ABX-101 after safety signal",
            "company": "ACME Pharma Inc.",
            "drug": "ABX-101",
            "summary": "Phase III product update",
        },
        "raw": {
            "title": "FDA label change for ACME Pharma's ABX-101 after safety signal",
            "description": "Serious adverse event reported during phase III study.",
        },
        "identifiers": {"set_id": "12345"},
    }


def test_pipeline_is_deterministic_for_same_input() -> None:
    pipeline = WorkerPipeline(checkpoint_store=MemoryCheckpointStore())
    first = pipeline.process(sample_payload(), transport="jsonl")
    second = pipeline.process(sample_payload(), transport="jsonl")

    assert first is not None
    assert second is None
    assert first.classifications["signal_class"] == "regulatory"
    assert "trial_phase" in first.classifications["signal_types"]
    assert first.entities["drugs"] == ["ABX-101"]


def test_pipeline_outputs_same_structure_for_replay_and_kafka_paths() -> None:
    payload = sample_payload()

    replay_pipeline = WorkerPipeline()
    kafka_pipeline = WorkerPipeline()

    replay_output = replay_pipeline.process(payload, transport="jsonl")
    kafka_output = kafka_pipeline.process(payload, transport="kafka")

    assert replay_output is not None
    assert kafka_output is not None
    assert replay_output.idempotency_key == kafka_output.idempotency_key
    assert replay_output.entities == kafka_output.entities
    assert replay_output.classifications == kafka_output.classifications
