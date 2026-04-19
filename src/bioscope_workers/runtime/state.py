from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class CheckpointStore(ABC):
    @abstractmethod
    def seen(self, key: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def mark(self, key: str) -> None:
        raise NotImplementedError


class MemoryCheckpointStore(CheckpointStore):
    def __init__(self) -> None:
        self._keys: set[str] = set()

    def seen(self, key: str) -> bool:
        return key in self._keys

    def mark(self, key: str) -> None:
        self._keys.add(key)


class FileCheckpointStore(CheckpointStore):
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._keys: set[str] = set()
        if self.path.exists():
            self._keys.update(line.strip() for line in self.path.read_text(encoding="utf-8").splitlines() if line.strip())

    def seen(self, key: str) -> bool:
        return key in self._keys

    def mark(self, key: str) -> None:
        if key in self._keys:
            return
        self._keys.add(key)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(f"{key}\n")


class CursorStore(ABC):
    @abstractmethod
    def load(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def save(self, position: int) -> None:
        raise NotImplementedError


class MemoryCursorStore(CursorStore):
    def __init__(self, position: int = 0) -> None:
        self._position = position

    def load(self) -> int:
        return self._position

    def save(self, position: int) -> None:
        self._position = position


class FileCursorStore(CursorStore):
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> int:
        if not self.path.exists():
            return 0
        raw_value = self.path.read_text(encoding="utf-8").strip()
        return int(raw_value) if raw_value else 0

    def save(self, position: int) -> None:
        self.path.write_text(f"{position}\n", encoding="utf-8")
