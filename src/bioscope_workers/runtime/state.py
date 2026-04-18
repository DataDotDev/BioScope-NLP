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
