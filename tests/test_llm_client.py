"""
LLM smoke tests. Skipped unless RUN_LLM_TESTS=1 (they hit the network).
"""
from __future__ import annotations

import os

import pytest

from ai_debugger.config import get_settings
from ai_debugger.core.embeddings import EXPECTED_DIM, EmbeddingClient
from ai_debugger.core.llm_client import LLMClient

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_LLM_TESTS") != "1",
    reason="Set RUN_LLM_TESTS=1 to enable live LLM/embedding tests",
)


@pytest.mark.asyncio
async def test_llm_text_mode() -> None:
    llm = LLMClient(get_settings())
    out = await llm.chat(
        [{"role": "user", "content": "Reply with exactly: pong"}],
        output="text",
    )
    assert isinstance(out, str) and out.strip()


@pytest.mark.asyncio
async def test_llm_json_mode() -> None:
    llm = LLMClient(get_settings())
    out = await llm.chat(
        [
            {"role": "system", "content": 'Return JSON only: {"ok": true}'},
            {"role": "user", "content": "go"},
        ],
        output="json",
    )
    import json

    parsed = json.loads(out)
    assert "ok" in parsed


@pytest.mark.asyncio
async def test_embedding_dim() -> None:
    emb = EmbeddingClient(get_settings())
    vec = await emb.embed_one("hello world")
    assert len(vec) == EXPECTED_DIM
