from bioscope_workers.contracts.envelope import ValidationError, compute_idempotency_key, load_envelope


def sample_payload() -> dict:
    return {
        "schema_version": "1.0.0",
        "source": "ClinicalTrials.gov",
        "record_type": "trial",
        "observed_at": "2026-04-18T10:00:00Z",
        "ingested_at": "2026-04-18T10:00:05Z",
        "normalized": {
            "title": "Phase II study of BI-1234 for oncology",
            "company": "BioPharma Inc.",
            "drug": "BI-1234",
            "phase": "Phase II",
        },
        "raw": {"title": "Phase II study of BI-1234 for oncology", "description": "A clinical trial"},
        "identifiers": {"nct_id": "NCT00000001"},
    }


def test_load_envelope_accepts_canonical_payload() -> None:
    envelope = load_envelope(sample_payload())
    assert envelope.source == "ClinicalTrials.gov"
    assert envelope.normalized["drug"] == "BI-1234"


def test_compute_idempotency_key_is_deterministic() -> None:
    payload = sample_payload()
    assert compute_idempotency_key(payload) == compute_idempotency_key(payload)


def test_load_envelope_rejects_missing_fields() -> None:
    payload = sample_payload()
    del payload["raw"]
    try:
        load_envelope(payload)
    except ValidationError as exc:
        assert "missing required fields" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected ValidationError")
