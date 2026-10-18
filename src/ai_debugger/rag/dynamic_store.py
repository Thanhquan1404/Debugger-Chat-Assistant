"""
In-memory + JSONL store for DynamicMemory records.
Mirror of DocStore, but with `deleted_at` audit trail for replace operations.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import structlog

from ai_debugger.schemas import DynamicMemory

log = structlog.get_logger(__name__)


class DynamicStore:
    def __init__(self, jsonl_path: Path) -> None:
        self._path = jsonl_path
        self._by_id: dict[str, DynamicMemory] = {}
        self._deleted: set[str] = set()
        self._write_lock = asyncio.Lock()

    # ---------- read ----------

    def get(self, memory_id: str) -> DynamicMemory | None:
        if memory_id in self._deleted:
            return None
        return self._by_id.get(memory_id)

    def all(self) -> dict[str, DynamicMemory]:
        return {k: v for k, v in self._by_id.items() if k not in self._deleted}

    def __len__(self) -> int:
        return len(self.all())

    def __contains__(self, memory_id: str) -> bool:
        return self.get(memory_id) is not None

    # ---------- load ----------

    def load(self) -> int:
        self._by_id.clear()
        self._deleted.clear()
        if not self._path.exists():
            log.info("dynamic_store.empty", path=str(self._path))
            return 0

        with self._path.open("r", encoding="utf-8-sig") as f:
            for lineno, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError as exc:
                    log.warning("dynamic_store.bad_json", lineno=lineno, error=str(exc))
                    continue
                # Tombstone record?
                if payload.get("_deleted") and payload.get("memory_id"):
                    self._deleted.add(payload["memory_id"])
                    continue
                try:
                    mem = DynamicMemory.model_validate(payload)
                except Exception as exc:
                    log.warning("dynamic_store.bad_record", lineno=lineno, error=str(exc))
                    continue
                self._by_id[mem.memory_id] = mem

        log.info("dynamic_store.loaded", path=str(self._path), count=len(self.all()))
        return len(self.all())

    # ---------- write ----------

    async def append_and_upsert(self, mem: DynamicMemory) -> None:
        async with self._write_lock:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            line = json.dumps(mem.model_dump(mode="json"), ensure_ascii=False)
            with self._path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
            self._by_id[mem.memory_id] = mem
            self._deleted.discard(mem.memory_id)

    async def mark_deleted(self, memory_id: str) -> None:
        """Append tombstone + remove from in-memory index."""
        async with self._write_lock:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            tombstone = json.dumps({"_deleted": True, "memory_id": memory_id}, ensure_ascii=False)
            with self._path.open("a", encoding="utf-8") as f:
                f.write(tombstone + "\n")
            self._by_id.pop(memory_id, None)
            self._deleted.add(memory_id)
        log.info("dynamic_store.tombstoned", memory_id=memory_id)