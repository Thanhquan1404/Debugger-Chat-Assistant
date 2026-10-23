from __future__ import annotations

import json

from fastapi.testclient import TestClient

from ai_debugger.core.llm_client import StreamDelta
from ai_debugger.main import create_app
from ai_debugger.rag.retriever import RetrievalResult
from tests.conftest import FakeLLM, FakeRetriever


def _parse_sse(text: str) -> list[dict]:
    events: list[dict] = []
    current: dict = {"event": None, "data": None}
    for line in text.splitlines():
        if line.startswith(": "):  # heartbeat comment
            continue
        if line.startswith("event: "):
            current["event"] = line[7:]
        elif line.startswith("data: "):
            current["data"] = line[6:]
        elif line == "":
            if current["event"]:
                events.append(current)
            current = {"event": None, "data": None}
    return events


def test_chat_rejects_empty_both(test_settings, fake_container):
    app = create_app(settings=test_settings, container=fake_container)
    with TestClient(app) as client:
        r = client.post("/api/chat/stream", data={})
    assert r.status_code == 400
    body = r.json()
    assert body["success"] is False
    assert "error" in body


def test_chat_stream_text_only(test_settings, fake_container, sample_doc):
    fake_container.retriever = FakeRetriever(
        RetrievalResult(query="q", docs=[sample_doc], static_hits=1)
    )
    fake_container.llm = FakeLLM(
        [StreamDelta(content="Hello "), StreamDelta(content="world"),
         StreamDelta(usage={"completion_tokens": 5}, is_usage_only=True)]
    )
    app = create_app(settings=test_settings, container=fake_container)
    with TestClient(app) as client:
        r = client.post(
            "/api/chat/stream",
            data={"query": "help me"},
            headers={"Accept": "text/event-stream"},
        )
    assert r.status_code == 200
    events = _parse_sse(r.text)
    types = [e["event"] for e in events]
    assert types[0] == "session"
    assert "sources" in types
    assert "answer_delta" in types
    assert types[-1] == "done"

    # Envelope shape
    first = json.loads(events[0]["data"])
    assert "data" in first and "ts" in first
    assert "session_id" in first["data"]

    # done contains message_id
    done = json.loads(events[-1]["data"])
    assert done["data"]["message_id"].startswith("msg_")
    assert done["data"]["answer"] == "Hello world"


def test_chat_persists_messages(test_settings, fake_container, sample_doc):
    fake_container.retriever = FakeRetriever(RetrievalResult(query="q", docs=[sample_doc]))
    fake_container.llm = FakeLLM([StreamDelta(content="ok")])
    app = create_app(settings=test_settings, container=fake_container)
    with TestClient(app) as client:
        r = client.post("/api/chat/stream", data={"query": "hello"})
    assert r.status_code == 200
    fs = fake_container.file_store
    # user message + assistant message should be persisted
    assert any(m.role == "user" for m in fs._messages.values())
    assert any(m.role == "assistant" for m in fs._messages.values())
