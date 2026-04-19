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

if [[ -z "${BIOSCOPE_WATCH_INPUT_FILE:-}" ]]; then
    echo "BIOSCOPE_WATCH_INPUT_FILE is required in your env file."
    exit 1
fi

if [[ -z "${BIOSCOPE_WATCH_OUTPUT_FILE:-}" ]]; then
    echo "BIOSCOPE_WATCH_OUTPUT_FILE is required in your env file."
    exit 1
fi

CMD=(python -m bioscope_workers --mode watch)

if [[ -n "${BIOSCOPE_WATCH_INPUT_FILE:-}" ]]; then
    CMD+=(--input "$BIOSCOPE_WATCH_INPUT_FILE")
fi
if [[ -n "${BIOSCOPE_WATCH_OUTPUT_FILE:-}" ]]; then
    CMD+=(--output "$BIOSCOPE_WATCH_OUTPUT_FILE")
fi
if [[ -n "${BIOSCOPE_WATCH_CURSOR_FILE:-}" ]]; then
    CMD+=(--cursor-file "$BIOSCOPE_WATCH_CURSOR_FILE")
fi
if [[ -n "${BIOSCOPE_WATCH_POLL_INTERVAL_SECONDS:-}" ]]; then
    CMD+=(--poll-interval-seconds "$BIOSCOPE_WATCH_POLL_INTERVAL_SECONDS")
fi
if [[ -n "${BIOSCOPE_WATCH_IDLE_LOG_INTERVAL_SECONDS:-}" ]]; then
    CMD+=(--idle-log-interval-seconds "$BIOSCOPE_WATCH_IDLE_LOG_INTERVAL_SECONDS")
fi
if [[ -n "${BIOSCOPE_LOG_LEVEL:-}" ]]; then
    CMD+=(--log-level "$BIOSCOPE_LOG_LEVEL")
fi

echo "Starting file watch bridge"
echo "  input:   ${BIOSCOPE_WATCH_INPUT_FILE:-}"
echo "  output:  ${BIOSCOPE_WATCH_OUTPUT_FILE:-}"
echo "  cursor:  ${BIOSCOPE_WATCH_CURSOR_FILE:-}"
echo "  poll:    ${BIOSCOPE_WATCH_POLL_INTERVAL_SECONDS:-2.0}s"

"${CMD[@]}"
