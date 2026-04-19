# BioScope NLP Workers

Separate worker repository for BioScope ingestion events. This repository consumes the same canonical event envelope in local JSONL replay mode and file-polling watch mode, enriches the event with NLP-derived intelligence, and writes enriched results to JSONL.

## Checklist

- [x] Separate Python worker repository created for BioScope NLP processing.
- [x] Shared contract layer added for canonical ingestion events.
- [x] Schema validation added for incoming envelopes.
- [x] Deterministic NLP enrichment pipeline added.
- [x] Entity extraction, company normalization, drug normalization, phase detection, and signal classification implemented.
- [x] JSONL replay mode added for local development.
- [x] File-polling watch mode added for low-complexity handoff.
- [x] Idempotency checkpointing added.
- [x] Tests added for contract validation, replay, and file-watch equivalence.
- [x] Structured run summary logging added for file-watch observability.
- [x] Enriched output contract validation added for downstream storage safety.
- [x] Shared schema bundle added for ingestion/worker consumption.
- [ ] Replace the rule-based NLP heuristics with model-backed extraction if higher recall is needed.
- [ ] Add a deployment manifest or container definition if this repo will be run in infrastructure.

## Repository Layout

```text
.
├── pyproject.toml
├── README.md
├── src/bioscope_workers
│   ├── cli.py
│   ├── contracts/
│   ├── runtime/
│   ├── services/
│   └── transports/
└── tests/
```

## Contract Strategy

The ingestion repository owns the canonical event envelope. This worker repository mirrors that schema in `bioscope_workers.contracts` and enforces compatibility using semantic versioning rules:

- `schema_version` is treated as a contract version, not a transport detail.
- The worker accepts any payload with the same major version.
- Incoming payloads are validated before enrichment begins.
- The enriched output is versioned independently so downstream consumers can evolve safely.

The practical sync rule is simple: if ingestion changes the envelope, worker changes must land in the same release window and the contract version must be bumped.

## Shared Schema Bundle

The shared contract bundle is checked into [schemas/bioscope.shared.contracts.json](schemas/bioscope.shared.contracts.json) so the ingestion and worker repositories can publish and consume the same field definitions.

- The ingestion repo should publish the same bundle version alongside its ingestion producer.
- This worker consumes the bundle through the local contract module and can export or load the same JSON artifact when needed.
- If the contract changes, both repos should bump the bundle version together.

## What Is Done

- Canonical contract validation is enforced before processing.
- The same input contract is accepted in JSONL replay and file-watch mode.
- Enrichment output is deterministic for the same payload.
- Idempotent processing is supported with a checkpoint store.
- The worker emits enriched output fields for entities, classifications, and alerts.

## What Still Needs To Be Done

- Add richer observability outputs (metrics export, dashboards, alerts).
- Add deployment/runtime manifests for production rollout.

## Input Contract

The worker expects the ingestion envelope to contain these keys:

- `schema_version`
- `source`
- `record_type`
- `observed_at`
- `ingested_at`
- `normalized`
- `raw`
- `identifiers`

Optional fields are preserved if present, but these are the required fields for validation and processing.

## Output Contract

The worker publishes enriched events with:

- `enrichment_schema_version`
- `input_event`
- `idempotency_key`
- `enriched_at`
- `entities`
- `classifications`
- `alerts`
- `transport`

## Local Development

Use JSONL files for replay and output.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
python -m bioscope_workers \
  --mode replay \
  --input examples/ingestion-events.jsonl \
  --output examples/enriched-events.jsonl
```

The replay command reads canonical ingestion events from a JSONL file, runs the same worker pipeline used in production, and writes enriched events to another JSONL file.

## Manual Test Walkthrough

Replay the external BioScope ingestion file to verify the worker end-to-end. The replay input file is located at `/Users/dedsec/Desktop/project/BioScope/out/ingestion.jsonl` (older local artifact; schema version is backfilled automatically in replay mode).

**Option 1: Quick replay (one command)**

```bash
./scripts/replay-bioscope-out.sh
```

This script handles venv activation, runs the replay, and displays a summary.

**Option 2: Replay with labels for comparison**

Run multiple replays with different labels to compare outputs:

```bash
./scripts/replay-bioscope-out.sh run-1
./scripts/replay-bioscope-out.sh run-2
./scripts/replay-bioscope-out.sh compare
```

The comparison shows whether the worker produces deterministic output (excluding timestamps).

**Option 3: Manual replay with full control**

```bash
source .venv/bin/activate
python -m bioscope_workers \
  --mode replay \
  --input /Users/dedsec/Desktop/project/BioScope/out/ingestion.jsonl \
  --output examples/enriched-from-bioscope-out.jsonl \
  --checkpoint examples/bioscope.checkpoints
```

Inspect the output (one enriched JSON object per line):

```bash
cat examples/enriched-from-bioscope-out.jsonl | head -n 1 | jq .
```

Each line contains the original event under `input_event` plus enrichment fields: `entities`, `classifications`, `alerts`.

A typical enriched record looks like this:

```json
{
  "alerts": {
    "emitted": true,
    "message": "trial signal detected for clinicaltrials.gov/clinical_trial involving Novo Nordisk A/S and NNC0662-0419",
    "severity": "medium"
  },
  "classifications": {
    "evidence": [
      "source:clinicaltrials.gov",
      "record_type:clinical_trial",
      "observed_at:2026-04-12T18:30:00Z",
      "ingested_at:2026-04-14T05:48:22.376460Z",
      "company:Novo Nordisk A/S",
      "drug:NNC0662-0419"
    ],
    "signal_class": "trial",
    "signal_types": ["trial_phase", "company_signal", "drug_signal"],
    "source_family": "clinical_trials"
  },
  "enrichment_schema_version": "1.0.0",
  "entities": {
    "companies": ["Novo Nordisk A/S"],
    "drugs": ["NNC0662-0419"],
    "mentions": ["Research", "Study", "Looking", "Into", "How"],
    "phases": []
  },
  "enriched_at": "2026-04-18T10:00:10.000000+00:00",
  "idempotency_key": "...",
  "input_event": {
    "schema_version": "1.0.0",
    "source": "clinicaltrials.gov",
    "record_type": "clinical_trial",
    "observed_at": "2026-04-12T18:30:00Z",
    "ingested_at": "2026-04-14T05:48:22.376460Z",
    "normalized": {
      "source": "clinicaltrials.gov",
      "record_type": "clinical_trial"
    },
    "raw": {
      "protocolSection": {
        "identificationModule": {
          "nctId": "NCT07525791"
        }
      }
    },
    "identifiers": {
      "nct_id": "NCT07525791"
    }
  },
  "transport": "jsonl"
}
```

What you should see:

- One line in examples/enriched-from-bioscope-out.jsonl for each input line.
- The same payload always produces the same idempotency key and the same enrichment fields.
- If you run the same input again with the same checkpoint file, duplicate events are skipped.
- The worker can process the existing `BioScope/out/ingestion.jsonl` file directly without creating a new sample file.

## File Bridge Mode

The worker consumes ingestion events from a shared JSONL file, processes them in a watch loop, and writes enrichment to another JSONL file.

Run the ingestion layer and this worker as separate processes against the same shared file path or mounted volume:

1. Start the ingestion service so it appends canonical events to `BIOSCOPE_WATCH_INPUT_FILE` using the shared schema bundle.
2. Start this worker so it polls the same file on an interval and writes enriched output to `BIOSCOPE_WATCH_OUTPUT_FILE`.
3. Keep both services independent: restart either one without restarting the other as long as the shared file paths remain available.

Configuration can come from command-line flags or environment variables:

- `BIOSCOPE_LOG_LEVEL` (default `INFO`)
- `BIOSCOPE_WATCH_INPUT_FILE`
- `BIOSCOPE_WATCH_OUTPUT_FILE` (default `examples/enriched-stream.jsonl`)
- `BIOSCOPE_WATCH_CURSOR_FILE` (default `examples/stream.cursor`)
- `BIOSCOPE_WATCH_POLL_INTERVAL_SECONDS` (default `2.0`)
- `BIOSCOPE_WATCH_IDLE_LOG_INTERVAL_SECONDS` (default `30.0`)
- `BIOSCOPE_REPLAY_INPUT`
- `BIOSCOPE_REPLAY_OUTPUT` (default `examples/enriched-events.jsonl`)
- `BIOSCOPE_REPLAY_CHECKPOINT` (default `examples/replay.checkpoints`)

```bash
cp .env.example .env
./scripts/run-watch.sh
```

The watch command consumes the same envelope format as replay mode, polls the input JSONL file at a configurable interval, and publishes enriched records to the output JSONL file. Each run logs a structured summary with received, processed, duplicate, and failed counts.

If you want to see the output, read from the output JSONL file with your preferred tooling. The worker sends the same JSON structure as replay mode, just through the file bridge instead of a broker.

In local development, the ingestion layer and this worker should be run independently. The ingestion process produces canonical events by appending to the shared input file, and this worker reads that file, enriches the payload, and appends a new message to the output file. That is the same low-overhead communication path you can use for the storage and backend layer.

## Run Commands

- `python -m venv .venv`: create an isolated local Python environment.
- `source .venv/bin/activate`: activate the virtual environment on macOS and Linux.
- `pip install -e '.[dev]'`: install the repository in editable mode with test dependencies.
- `cp .env.example .env`: create your environment file.
- `./scripts/run-local.sh`: run local replay mode using values from `.env`.
- `./scripts/run-local.sh .env.production`: run local replay mode with a specific env file.
- `python -m bioscope_workers --mode replay --input <input.jsonl> --output <output.jsonl>`: run local JSONL replay mode.
- `cat <output.jsonl>`: inspect the enriched JSONL output one line at a time.
- `./scripts/run-watch.sh`: run the file-polling bridge using values from `.env`.
- `./scripts/run-watch.sh .env.production`: run the file bridge with a specific env file.
- `python -m bioscope_workers --mode watch`: run the file-polling bridge using environment configuration.
- `pytest`: run the full test suite.

## Env-First Startup

Use the scripts in `scripts/` so all runtime values are loaded from env files.

1. Create your env file.

```bash
cp .env.example .env
```

2. Run local replay mode.

```bash
./scripts/run-local.sh
```

3. Run file bridge mode.

```bash
./scripts/run-watch.sh
```

For production-style runs, keep a separate env file (for example `.env.production`) and pass it as the first script argument.

## Example NLP Pipeline

The worker pipeline is intentionally deterministic and message-driven:

1. Validate the canonical envelope.
2. Compute an idempotency key from the normalized event content.
3. Extract entities from normalized fields and raw text.
4. Normalize company and drug names.
5. Detect trial phase and regulatory event signals.
6. Classify the signal and optionally emit alerts.
7. Persist output to JSONL.

## Tests

The tests verify that the same input produces the same enriched output regardless of whether it enters the worker through local replay or file-watch ingestion.

```bash
pytest
```

The current test coverage includes:

- canonical envelope validation
- idempotency key stability
- deterministic pipeline behavior
- replay and file-watch output equivalence
- shared schema bundle publication and consumption metadata

## How This Stays In Sync With Ingestion

This repository stays aligned with the ingestion repo by keeping the contract in a dedicated module, versioning the envelope explicitly, and failing fast on incompatible schema changes. In practice, this means:

- the ingestion repo publishes a versioned canonical envelope and appends it to the shared JSONL file
- this repo mirrors that contract in `bioscope_workers.contracts`
- any breaking envelope change requires a coordinated major version bump
- tests guard the contract and the deterministic enrichment output

## Notes

- The worker code currently uses deterministic heuristics so the same input always produces the same output.
- The repository is designed to be run as a separate service from the ingestion layer.
- The local replay path is intended for developer validation and backfills, not as a transport-specific code path.
- The file-watch path is the low-complexity communication path for keeping ingestion and enrichment loosely coupled.
