"""
In-memory full-payload store (D10) + append-only JSONL persistence.

Payload = full StaticErrorDoc. Loaded once at startup. Search never touches it;
hydration does. This is where solution/symptoms/root_cause live.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import structlog

from ai_debugger.schemas import StaticErrorDoc

log = structlog.get_logger(__name__)


class DocStoreError(RuntimeError):
    pass


class DocStore:
    """
    Runtime: dict {doc_id: StaticErrorDoc}.
    Persistence: append-only JSONL. On load, latest entry per doc_id wins.
    """

    def __init__(self, jsonl_path: Path) -> None:
        self._path = jsonl_path
        self._by_id: dict[str, StaticErrorDoc] = {}
        self._write_lock = asyncio.Lock()

    # ---------- read ----------

    def get(self, doc_id: str) -> StaticErrorDoc | None:
        return self._by_id.get(doc_id)

    def all(self) -> dict[str, StaticErrorDoc]:
        return dict(self._by_id)

    def __len__(self) -> int:
        return len(self._by_id)

    def __contains__(self, doc_id: str) -> bool:
        return doc_id in self._by_id

    # ---------- load ----------

    def load(self) -> int:
        """
        Load docs from JSONL into memory. Latest entry per doc_id wins.
        Returns number of unique docs loaded.
        """
        self._by_id.clear()
        if not self._path.exists():
            log.info("doc_store.empty", path=str(self._path))
            return 0

        with self._path.open("r", encoding="utf-8-sig") as f:
            for lineno, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                    doc = StaticErrorDoc.model_validate(payload)
                except Exception as exc:
                    log.error(
                        "doc_store.bad_line",
                        path=str(self._path),
                        lineno=lineno,
                        error=str(exc),
                    )
                    continue
                self._by_id[doc.doc_id] = doc

        log.info("doc_store.loaded", path=str(self._path), count=len(self._by_id))
        return len(self._by_id)

    # ---------- write ----------

    async def append_and_upsert(self, doc: StaticErrorDoc) -> None:
        """Append one doc to JSONL + update in-memory dict (atomic under lock)."""
        async with self._write_lock:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            line = json.dumps(doc.model_dump(mode="json"), ensure_ascii=False)
            with self._path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
            self._by_id[doc.doc_id] = doc

    async def append_many(self, docs: list[StaticErrorDoc]) -> None:
        if not docs:
            return
        async with self._write_lock:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with self._path.open("a", encoding="utf-8") as f:
                for doc in docs:
                    line = json.dumps(doc.model_dump(mode="json"), ensure_ascii=False)
                    f.write(line + "\n")
            for doc in docs:
                self._by_id[doc.doc_id] = doc
        log.info("doc_store.appended", n=len(docs))
