from __future__ import annotations

from pathlib import Path

import pytest

from ai_debugger.rag.dynamic_store import DynamicStore
from ai_debugger.schemas import DynamicMemory


def _mem(mid: str = "DYN_1", conf: float = 0.85) -> DynamicMemory:
    return DynamicMemory(
        memory_id=mid,
        error_content="503 session timeout dkmh",
        llm_verified_solution="clear cookie",
        confidence_score=conf,
    )


@pytest.mark.asyncio
async def test_append_and_reload(tmp_path: Path) -> None:
    store = DynamicStore(tmp_path / "m.jsonl")
    await store.append_and_upsert(_mem("D1"))
    await store.append_and_upsert(_mem("D2"))

    store2 = DynamicStore(tmp_path / "m.jsonl")
    n = store2.load()
    assert n == 2
    assert store2.get("D1") is not None


@pytest.mark.asyncio
async def test_tombstone_hides_entry(tmp_path: Path) -> None:
    store = DynamicStore(tmp_path / "m.jsonl")
    await store.append_and_upsert(_mem("D1"))
    await store.mark_deleted("D1")
    assert store.get("D1") is None
    assert "D1" not in store
    assert len(store) == 0

    store2 = DynamicStore(tmp_path / "m.jsonl")
    store2.load()
    assert store2.get("D1") is None
    assert len(store2) == 0


@pytest.mark.asyncio
async def test_tombstone_then_reinsert(tmp_path: Path) -> None:
    store = DynamicStore(tmp_path / "m.jsonl")
    await store.append_and_upsert(_mem("D1"))
    await store.mark_deleted("D1")
    await store.append_and_upsert(_mem("D1", conf=0.95))
    assert store.get("D1").confidence_score == 0.95