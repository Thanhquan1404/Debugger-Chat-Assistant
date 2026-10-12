"""
Streaming unit tests. Use a fake AsyncOpenAI client to avoid network.
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from types import SimpleNamespace

import pytest

from ai_debugger.config import Settings
from ai_debugger.core.llm_client import LLMClient


class _FakeStream:
    def __init__(self, chunks):
        self._chunks = chunks

    def __aiter__(self) -> AsyncIterator:
        return self._gen()

    async def _gen(self):
        for c in self._chunks:
            yield c


def _chunk(
    *,
    content: str | None = None,
    reasoning: str | None = None,
    finish: str | None = None,
    usage: dict | None = None,
    empty_choices: bool = False,
):
    delta_kwargs = {}
    if content is not None:
        delta_kwargs["content"] = content
    if reasoning is not None:
        delta_kwargs["reasoning_content"] = reasoning

    delta = SimpleNamespace(**delta_kwargs, model_extra={})

    choices = [] if empty_choices else [SimpleNamespace(delta=delta, finish_reason=finish)]

    usage_obj = None
    if usage is not None:
        usage_obj = SimpleNamespace(model_dump=lambda: dict(usage), model_extra={})

    return SimpleNamespace(choices=choices, usage=usage_obj)


@pytest.fixture
def settings() -> Settings:
    return Settings(LLM_ENDPOINT="http://x", LLM_API_KEY="k", LLM_MODEL="test-model")


@pytest.mark.asyncio
async def test_stream_emits_content_and_usage(settings, monkeypatch):
    llm = LLMClient(settings)
    chunks = [
        _chunk(content="Hello "),
        _chunk(content="world"),
        _chunk(finish="stop"),
        _chunk(
            empty_choices=True,
            usage={"completion_tokens": 3, "completion_tokens_details": {"reasoning_tokens": 2}},
        ),
    ]

    async def fake_create(**kwargs):
        return _FakeStream(chunks)

    monkeypatch.setattr(llm._client.chat.completions, "create", fake_create)

    deltas = [d async for d in llm.stream([{"role": "user", "content": "hi"}])]
    contents = "".join(d.content for d in deltas)
    assert contents == "Hello world"
    assert deltas[-1].usage is not None
    assert deltas[-1].usage["completion_tokens_details"]["reasoning_tokens"] == 2
    assert deltas[-1].is_usage_only is True


@pytest.mark.asyncio
async def test_stream_reasoning_field_defensive(settings, monkeypatch):
    """Providers may use 'reasoning_content' or 'reasoning'."""
    llm = LLMClient(settings)
    chunks = [_chunk(content="ans", reasoning="because")]
    monkeypatch.setattr(
        llm._client.chat.completions,
        "create",
        lambda **kw: _FakeStream(chunks),
    )
    # Wrap in coroutine because method is called with `await`
    async def fake(**kw):
        return _FakeStream(chunks)
    monkeypatch.setattr(llm._client.chat.completions, "create", fake)

    deltas = [d async for d in llm.stream([{"role": "user", "content": "hi"}])]
    assert deltas[0].reasoning == "because"


@pytest.mark.asyncio
async def test_stream_skips_empty_chunks(settings, monkeypatch):
    llm = LLMClient(settings)
    chunks = [_chunk(), _chunk(content="x"), _chunk()]

    async def fake(**kw):
        return _FakeStream(chunks)
    monkeypatch.setattr(llm._client.chat.completions, "create", fake)

    deltas = [d async for d in llm.stream([{"role": "user", "content": "hi"}])]
    assert len(deltas) == 1
    assert deltas[0].content == "x"


@pytest.mark.asyncio
async def test_parse_chunk_none_when_empty(settings):
    chunk = _chunk()  # nothing set
    assert LLMClient._parse_chunk(chunk) is None
