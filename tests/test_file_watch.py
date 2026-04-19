import json

from bioscope_workers.runtime.file_watch import read_new_jsonl_records
from bioscope_workers.runtime.state import FileCursorStore, MemoryCursorStore


def test_read_new_jsonl_records_reads_only_appended_lines(tmp_path) -> None:
    input_path = tmp_path / "ingestion.jsonl"
    input_path.write_text(
        json.dumps({"id": 1}) + "\n" + json.dumps({"id": 2}) + "\n",
        encoding="utf-8",
    )

    records, offset = read_new_jsonl_records(input_path, 0)

    assert [record["id"] for record in records] == [1, 2]
    assert offset == input_path.stat().st_size

    input_path.write_text(input_path.read_text(encoding="utf-8") + json.dumps({"id": 3}) + "\n", encoding="utf-8")

    new_records, new_offset = read_new_jsonl_records(input_path, offset)

    assert [record["id"] for record in new_records] == [3]
    assert new_offset == input_path.stat().st_size


def test_cursor_store_round_trip(tmp_path) -> None:
    cursor_path = tmp_path / "stream.cursor"
    store = FileCursorStore(cursor_path)

    assert store.load() == 0
    store.save(128)
    assert store.load() == 128


def test_memory_cursor_store_round_trip() -> None:
    store = MemoryCursorStore()
    assert store.load() == 0
    store.save(42)
    assert store.load() == 42
