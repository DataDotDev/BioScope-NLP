from bioscope_workers.contracts.enrichment import validate_enriched_event
from bioscope_workers.contracts.envelope import ValidationError


def sample_enriched_payload() -> dict:
    return {
        "transport": "jsonl",
        "idempotency_key": "abc123",
        "enrichment_schema_version": "1.0.0",
        "input_event": {"schema_version": "1.0.0"},
        "entities": {"companies": [], "drugs": [], "phases": [], "mentions": []},
        "classifications": {"signal_class": "unknown", "signal_types": [], "evidence": [], "source_family": "unknown"},
        "alerts": {"emitted": False, "severity": "none", "message": ""},
        "enriched_at": "2026-04-19T10:00:00+00:00",
    }


def test_validate_enriched_event_accepts_valid_payload() -> None:
    validate_enriched_event(sample_enriched_payload())


def test_validate_enriched_event_rejects_missing_fields() -> None:
    payload = sample_enriched_payload()
    del payload["alerts"]

    try:
        validate_enriched_event(payload)
    except ValidationError as exc:
        assert "missing required fields" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected ValidationError")
