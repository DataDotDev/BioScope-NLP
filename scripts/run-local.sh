#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

source "$SCRIPT_DIR/load-env.sh" "${1:-}"

if [[ ! -f "$REPO_DIR/.venv/bin/activate" ]]; then
    echo "Virtual environment not found at $REPO_DIR/.venv"
    echo "Run: python -m venv .venv"
    exit 1
fi

source "$REPO_DIR/.venv/bin/activate"

cd "$REPO_DIR"

if ! python -c "import bioscope_workers" 2>/dev/null; then
    echo "Installing bioscope_workers package (dev extras)..."
    pip install -e '.[dev]' -q
fi

if [[ -z "${BIOSCOPE_REPLAY_INPUT:-}" ]]; then
    echo "BIOSCOPE_REPLAY_INPUT is required in your env file."
    exit 1
fi

OUTPUT_PATH="${BIOSCOPE_REPLAY_OUTPUT:-$REPO_DIR/examples/enriched-events.jsonl}"
CHECKPOINT_PATH="${BIOSCOPE_REPLAY_CHECKPOINT:-$REPO_DIR/examples/replay.checkpoints}"

CMD=(
    python -m bioscope_workers
    --mode replay
    --input "$BIOSCOPE_REPLAY_INPUT"
    --output "$OUTPUT_PATH"
    --checkpoint "$CHECKPOINT_PATH"
)

if [[ -n "${BIOSCOPE_LOG_LEVEL:-}" ]]; then
    CMD+=(--log-level "$BIOSCOPE_LOG_LEVEL")
fi

echo "Starting local replay run"
echo "  input:      $BIOSCOPE_REPLAY_INPUT"
echo "  output:     $OUTPUT_PATH"
echo "  checkpoint: $CHECKPOINT_PATH"

"${CMD[@]}"
