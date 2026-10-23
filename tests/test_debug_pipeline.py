from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import yaml

from ai_debugger.config import Settings
from ai_debugger.core.llm_client import StreamDelta
from ai_debugger.core.prompt_loader import PromptLoader
from ai_debugger.pipeline import build_labeled_query, run_debug_pipeline
from ai_debugger.rag.retriever import RetrievalResult, RetrievedDoc


class FakeRetriever:
    def __init__(self, result: RetrievalResult):
        self._result = result

    async def retrieve(self, query: str) -> RetrievalResult:
        return self._result


class FakeLLM:
    def __init__(self, deltas: list[StreamDelta]):
        self._deltas = deltas

    async def stream(self, messages, **kwargs) -> AsyncIterator[StreamDelta]:
        for d in self._deltas:
            yield d


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(LLM_ENDPOINT="http://x", LLM_API_KEY="k")


@pytest.fixture
def prompt_loader(tmp_path) -> PromptLoader:
    d = tmp_path / "prompts"
    d.mkdir()
    (d / "system_debug.yaml").write_text(
        yaml.safe_dump(
            {
                "name": "system_debug",
                "version": 1,
                "system": "You are a debugger.",
                "user_template": (
                    "OCR={{ ocr_text }}\nUSER={{ user_prompt }}\nCTX={{ context_block }}"
                ),
            }
        ),
        encoding="utf-8",
    )
    return PromptLoader(d)


def _doc() -> RetrievedDoc:
    return RetrievedDoc(
        doc_id="D1",
        source="static",
        score=0.9,
        error_content="err",
        system_name="SYS",
        solution_summary="fix",
        solution_steps=["do x"],
        tags=["t"],
    )


def test_build_labeled_query_both():
    q = build_labeled_query("log text", "question")
    assert "[FROM_IMAGE]" in q
    assert "[FROM_USER]" in q


def test_build_labeled_query_only_image():
    q = build_labeled_query("log", "")
    assert "[FROM_IMAGE]" in q
    assert "[FROM_USER]" not in q


@pytest.mark.asyncio
async def test_pipeline_rejects_empty_inputs(settings, prompt_loader):
    r = FakeRetriever(RetrievalResult(query="", docs=[]))
    llm = FakeLLM([])
    events = [
        ev
        async for ev in run_debug_pipeline(
            ocr_text="",
            user_prompt="   ",
            message_id="m1",
            settings=settings,
            retriever=r,
            llm=llm,
            prompt_loader=prompt_loader,
        )
    ]
    assert len(events) == 1
    assert events[0].type == "error"


@pytest.mark.asyncio
async def test_pipeline_happy_path(settings, prompt_loader):
    r = FakeRetriever(RetrievalResult(query="q", docs=[_doc()], static_hits=1))
    llm = FakeLLM(
        [
            StreamDelta(content="Hello "),
            StreamDelta(content="world"),
            StreamDelta(usage={"completion_tokens": 5}, is_usage_only=True),
        ]
    )
    events = [
        ev
        async for ev in run_debug_pipeline(
            ocr_text="log line",
            user_prompt="what?",
            message_id="m1",
            settings=settings,
            retriever=r,
            llm=llm,
            prompt_loader=prompt_loader,
        )
    ]
    types = [e.type for e in events]
    assert types[0] == "sources"
    assert "answer_delta" in types
    assert types[-1] == "done"

    done = events[-1]
    assert done.data["message_id"] == "m1"
    assert done.data["answer"] == "Hello world"
    assert done.data["sources"][0]["doc_id"] == "D1"
    assert done.data["usage"]["completion_tokens"] == 5


@pytest.mark.asyncio
async def test_pipeline_empty_retrieval_still_calls_llm(settings, prompt_loader):
    """Q6 = (a): empty retrieval → still call LLM; system prompt handles fallback."""
    r = FakeRetriever(RetrievalResult(query="q", docs=[]))
    llm = FakeLLM([StreamDelta(content="Tôi cần thêm thông tin.")])
    events = [
        ev
        async for ev in run_debug_pipeline(
            ocr_text="x",
            user_prompt="y",
            message_id="m1",
            settings=settings,
            retriever=r,
            llm=llm,
            prompt_loader=prompt_loader,
        )
    ]
    sources = events[0]
    assert sources.type == "sources"
    assert sources.data["is_empty"] is True
    assert any(e.type == "answer_delta" for e in events)
