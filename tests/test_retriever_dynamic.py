"""
Dynamic retrieval + weighted merge.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from ai_debugger.config import Settings
from ai_debugger.rag.doc_store import DocStore
from ai_debugger.rag.dynamic_store import DynamicStore
from ai_debugger.rag.milvus_client import MilvusStore
from ai_debugger.rag.retriever import Retriever
from ai_debugger.schemas import DynamicMemory, StaticErrorDoc


class FakeEmbedder:
    async def embed(self, texts):
        return [[0.5] * 1536 for _ in texts]


def _static(doc_id: str, error_content: str) -> StaticErrorDoc:
    return StaticErrorDoc.model_validate({
        "doc_id": doc_id, "system_name": "SYS", "error_content": error_content,
        "solution": {"summary": "fix", "steps": ["s"]}, "tags": [],
    })


@pytest.mark.asyncio
async def test_dynamic_only_triggers_flag(tmp_path: Path):
    settings = Settings(
        _env_file=None, LLM_ENDPOINT="http://x", LLM_API_KEY="k",
        MILVUS_URI=str(tmp_path / "t.db"), DOC_STORE_DIR=tmp_path,
        SCORE_THRESHOLD=0.0, LEARNING_CONFIDENCE_PROTECT=0.85,
    )
    milvus = MilvusStore(settings)
    milvus.create_collections()

    static_store = DocStore(tmp_path / "static_store" / "docs.jsonl")
    static_store.load()

    dyn_store = DynamicStore(tmp_path / "dynamic_store" / "m.jsonl")
    await dyn_store.append_and_upsert(DynamicMemory(
        memory_id="DYN_1", error_content="503 on portal",
        llm_verified_solution="clear cookies", confidence_score=0.82,
    ))
    milvus.upsert_dynamic([{
        "memory_id": "DYN_1", "vector": [0.5] * 1536,
        "confidence_score": 0.82, "occurrence_count": 1, "tags": [],
    }])

    r = Retriever(settings, milvus, static_store, FakeEmbedder(), dyn_store)
    result = await r.retrieve("q")
    assert result.dynamic_only is True
    assert result.may_be_hallucinated is True   # 0.82 < 0.85
    assert len(result.docs) == 1
    assert result.docs[0].source == "dynamic"


@pytest.mark.asyncio
async def test_static_plus_dynamic_weighted(tmp_path: Path):
    settings = Settings(
        _env_file=None, LLM_ENDPOINT="http://x", LLM_API_KEY="k",
        MILVUS_URI=str(tmp_path / "t.db"), DOC_STORE_DIR=tmp_path,
        SCORE_THRESHOLD=0.0, STATIC_WEIGHT=0.7, DYNAMIC_WEIGHT=0.3, TOP_N_FINAL=3,
    )
    milvus = MilvusStore(settings)
    milvus.create_collections()

    static_store = DocStore(tmp_path / "static_store" / "docs.jsonl")
    await static_store.append_and_upsert(_static("D1", "503 on portal"))
    milvus.upsert_static([{
        "doc_id": "D1", "vector": [0.5] * 1536,
        "system_name": "SYS", "error_code": "", "tags": [], "verified": True,
    }])

    dyn_store = DynamicStore(tmp_path / "dynamic_store" / "m.jsonl")
    await dyn_store.append_and_upsert(DynamicMemory(
        memory_id="DYN_1", error_content="503 on portal new",
        llm_verified_solution="fix", confidence_score=0.88,
    ))
    milvus.upsert_dynamic([{
        "memory_id": "DYN_1", "vector": [0.5] * 1536,
        "confidence_score": 0.88, "occurrence_count": 1, "tags": [],
    }])

    r = Retriever(settings, milvus, static_store, FakeEmbedder(), dyn_store)
    result = await r.retrieve("q")
    assert result.dynamic_only is False
    assert result.may_be_hallucinated is False
    # Static weighted 0.7 > dynamic weighted 0.3 (same raw score)
    assert result.docs[0].source == "static"