#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

LABEL="${1:-default}"
INPUT_FILE="/Users/dedsec/Desktop/project/BioScope/out/ingestion.jsonl"
OUTPUT_FILE="$REPO_DIR/examples/enriched-from-bioscope-out-${LABEL}.jsonl"
CHECKPOINT_FILE="$REPO_DIR/examples/bioscope.checkpoints-${LABEL}"

# Handle compare subcommand
if [ "$LABEL" = "compare" ]; then
    echo "BioScope NLP Worker - Replay Comparison"
    echo "========================================"
    echo ""
    
    FILE1="$REPO_DIR/examples/enriched-from-bioscope-out-run-1.jsonl"
    FILE2="$REPO_DIR/examples/enriched-from-bioscope-out-run-2.jsonl"
    
    if [ ! -f "$FILE1" ]; then
        echo "Error: First output file not found: $FILE1"
        echo "Run: ./scripts/replay-bioscope-out.sh run-1"
        exit 1
    fi
    
    if [ ! -f "$FILE2" ]; then
        echo "Error: Second output file not found: $FILE2"
        echo "Run: ./scripts/replay-bioscope-out.sh run-2"
        exit 1
    fi
    
    COUNT1=$(wc -l < "$FILE1")
    COUNT2=$(wc -l < "$FILE2")
    
    echo "Run 1: $COUNT1 records"
    echo "Run 2: $COUNT2 records"
    echo ""
    
    if [ "$COUNT1" -eq "$COUNT2" ]; then
        echo "✓ Record counts match"
        
        # Compare first records
        DIFF=$(diff <(head -n 1 "$FILE1" | jq .) <(head -n 1 "$FILE2" | jq .) || true)
        if [ -z "$DIFF" ]; then
            echo "✓ First records are identical"
        else
            echo "⚠ First records differ:"
            echo "$DIFF"
        fi
    else
        echo "✗ Record counts differ"
    fi
    
    echo ""
    echo "Files:"
    echo "  Run 1: $FILE1"
    echo "  Run 2: $FILE2"
    exit 0
fi

echo "BioScope NLP Worker - External Replay Helper"
echo "=============================================="
echo ""

# Activate venv
if [ ! -f "$REPO_DIR/.venv/bin/activate" ]; then
    echo "Error: Virtual environment not found at $REPO_DIR/.venv"
    echo "Run: python -m venv .venv && source .venv/bin/activate && pip install -e '.[dev]'"
    exit 1
fi

source "$REPO_DIR/.venv/bin/activate"

# Ensure the package is installed in the venv
if ! python -c "import bioscope_workers" 2>/dev/null; then
    echo "Installing bioscope_workers package..."
    pip install -e "${REPO_DIR}[dev]" -q
fi

# Create output directory

mkdir -p "$REPO_DIR/examples"

if [ ! -f "$INPUT_FILE" ]; then
    echo "Error: Input file not found at $INPUT_FILE"
    exit 1
fi

echo "Label:  $LABEL"
echo "Input:  $INPUT_FILE"
echo "Output: $OUTPUT_FILE"
echo ""
echo "Processing..."

python -m bioscope_workers \
    --mode replay \
    --input "$INPUT_FILE" \
    --output "$OUTPUT_FILE" \
    --checkpoint "$CHECKPOINT_FILE"

# Display summary
if [ -f "$OUTPUT_FILE" ]; then
    RECORD_COUNT=$(wc -l < "$OUTPUT_FILE")
    echo ""
    echo "✓ Replay complete"
    echo "  Output records: $RECORD_COUNT"
    echo "  Output file: $OUTPUT_FILE"
    echo ""
    echo "View first record:"
    echo "  cat $OUTPUT_FILE | head -n 1 | jq ."
    echo ""
    echo "Run again with a different label to compare:"
    echo "  ./scripts/replay-bioscope-out.sh run-2"
    echo "  ./scripts/replay-bioscope-out.sh compare"
else
    echo "Error: Output file was not created"
    exit 1
fi
