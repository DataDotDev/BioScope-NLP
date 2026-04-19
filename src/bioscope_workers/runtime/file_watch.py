from __future__ import annotations

from pathlib import Path
import json
from typing import Any


def read_new_jsonl_records(path: str | Path, offset: int) -> tuple[list[dict[str, Any]], int]:
    source_path = Path(path)
    if not source_path.exists():
        return [], offset

    file_size = source_path.stat().st_size
    if offset > file_size:
        offset = 0

    records: list[dict[str, Any]] = []
    next_offset = offset

    with source_path.open("r", encoding="utf-8") as handle:
        handle.seek(offset)
        while True:
            line_start = handle.tell()
            raw_line = handle.readline()
            if not raw_line:
                break

            stripped = raw_line.strip()
            if not stripped:
                next_offset = handle.tell()
                continue

            try:
                records.append(json.loads(stripped))
                next_offset = handle.tell()
            except json.JSONDecodeError:
                handle.seek(line_start)
                break

    return records, next_offset
