from __future__ import annotations

from pathlib import Path

import pytest

from ai_debugger.config import Settings
from ai_debugger.rag.doc_store import DocStore
from ai_debugger.rag.milvus_client import MilvusStore
from ai_debugger.rag.retriever import Retriever
from ai_debugger.schemas import StaticErrorDoc


class FakeEmbedder:
    """Deterministic embedder — stable vector from text hash."""

    async def embed(self, texts: list[str]) -> list[list[float]]:
        out = []
        for t in texts:
            seed = abs(hash(t)) % 1000
            out.append([seed / 1000.0] * 1536)
        return out

    async def embed_one(self, text: str) -> list[float]:
        [v] = await self.embed([text])
        return v


def _doc(doc_id: str, error_content: str, solution: str = "do x") -> StaticErrorDoc:
    return StaticErrorDoc.model_validate(
        {
            "doc_id": doc_id,
            "system_name": "SYS",
            "error_content": error_content,
            "solution": {"summary": solution, "steps": ["s1", "s2"]},
            "tags": ["t"],
            "symptoms": ["sym1"],
            "root_cause": "rc",
        }
    )


@pytest.fixture
def retriever_env(tmp_path: Path):
    settings = Settings(
        LLM_ENDPOINT="http://x",
        LLM_API_KEY="k",
        MILVUS_URI=str(tmp_path / "test.db"),
        DOC_STORE_DIR=tmp_path,
        TOP_K_PER_COLLECTION=5,
        TOP_N_FINAL=3,
        SCORE_THRESHOLD=0.0,  # accept everything in tests
    )
    milvus = MilvusStore(settings)
    milvus.create_collections()

    doc_store = DocStore(tmp_path / "static_store" / "docs.jsonl")
    doc_store.load()

    # Insert 2 static docs directly
    import asyncio

    async def seed():
        d1 = _doc("D1", "503 session timeout dkmh", "clear cookie")
        d2 = _doc("D2", "404 not found api", "check route")
        milvus.upsert_static(
            [
                {
                    "doc_id": d1.doc_id,
                    "vector": [0.5] * 1536,
                    "system_name": "SYS",
                    "error_code": "",
                    "tags": ["t"],
                    "verified": True,
                },
                {
                    "doc_id": d2.doc_id,
                    "vector": [0.9] * 1536,
                    "system_name": "SYS",
                    "error_code": "",
                    "tags": ["t"],
                    "verified": True,
                },
            ]
        )
        await doc_store.append_many([d1, d2])

    asyncio.run(seed())
    return settings, milvus, doc_store


@pytest.mark.asyncio
async def test_retrieve_hydrates_static(retriever_env):
    settings, milvus, doc_store = retriever_env
    r = Retriever(settings, milvus, doc_store, FakeEmbedder())
    result = await r.retrieve("anything")
    assert len(result.docs) >= 1
    assert result.docs[0].source == "static"
    assert result.docs[0].solution_summary in {"clear cookie", "check route"}
    assert result.docs[0].error_content


@pytest.mark.asyncio
async def test_top_n_cut(retriever_env):
    settings, milvus, doc_store = retriever_env
    # Force top_n = 1
    s = settings.model_copy(update={"top_n_final": 1})
    r = Retriever(s, milvus, doc_store, FakeEmbedder())
    result = await r.retrieve("q")
    assert len(result.docs) == 1


@pytest.mark.asyncio
async def test_empty_when_no_hits(tmp_path: Path):
    settings = Settings(
        LLM_ENDPOINT="http://x",
        LLM_API_KEY="k",
        MILVUS_URI=str(tmp_path / "test.db"),
        SCORE_THRESHOLD=0.99,  # unreachable
    )
    milvus = MilvusStore(settings)
    milvus.create_collections()
    doc_store = DocStore(tmp_path / "static_store" / "docs.jsonl")
    doc_store.load()
    milvus.upsert_static(
        [
            {
                "doc_id": "D1",
                "vector": [0.1] * 1536,
                "system_name": "S",
                "error_code": "",
                "tags": [],
                "verified": True,
            }
        ]
    )
    r = Retriever(settings, milvus, doc_store, FakeEmbedder())
    result = await r.retrieve("q")
    assert result.is_empty
    assert result.to_context_block() == ""


@pytest.mark.asyncio
async def test_empty_query_rejected(retriever_env):
    settings, milvus, doc_store = retriever_env
    r = Retriever(settings, milvus, doc_store, FakeEmbedder())
    with pytest.raises(ValueError):
        await r.retrieve("   ")


def test_context_block_format(retriever_env):
    settings, milvus, doc_store = retriever_env
    # Sync check on dataclass formatting
    from ai_debugger.rag.retriever import RetrievedDoc

    d = RetrievedDoc(
        doc_id="D1",
        source="static",
        score=0.9,
        error_content="err",
        system_name="SYS",
        error_code="E1",
        root_cause="rc",
        symptoms=["s1"],
        solution_summary="fix",
        solution_steps=["step1"],
        tags=["x"],
    )
    block = d.to_context_block(1)
    assert "[DOC_1]" in block
    assert "doc_id=D1" in block
    assert "solution: fix" in block
    assert "1. step1" in block
