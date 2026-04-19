#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

ENV_FILE_INPUT="${1:-}"
if [[ -n "$ENV_FILE_INPUT" ]]; then
    if [[ "$ENV_FILE_INPUT" = /* ]]; then
        ENV_FILE="$ENV_FILE_INPUT"
    else
        ENV_FILE="$REPO_DIR/$ENV_FILE_INPUT"
    fi
elif [[ -n "${BIOSCOPE_ENV_FILE:-}" ]]; then
    if [[ "$BIOSCOPE_ENV_FILE" = /* ]]; then
        ENV_FILE="$BIOSCOPE_ENV_FILE"
    else
        ENV_FILE="$REPO_DIR/$BIOSCOPE_ENV_FILE"
    fi
else
    ENV_FILE="$REPO_DIR/.env"
fi

if [[ -f "$ENV_FILE" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +a
    echo "Loaded environment from: $ENV_FILE"
else
    echo "Environment file not found at: $ENV_FILE"
    echo "Copy .env.example to .env and update values."
    exit 1
fi
