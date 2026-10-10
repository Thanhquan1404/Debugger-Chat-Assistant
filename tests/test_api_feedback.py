from __future__ import annotations

from fastapi.testclient import TestClient

from ai_debugger.core.llm_client import StreamDelta
from ai_debugger.main import create_app
from ai_debugger.rag.retriever import RetrievalResult
from tests.conftest import FakeLLM, FakeRetriever


def _get_last_assistant_message_id(client: TestClient, container) -> str:
    # Simplest: after a chat, read from file store
    return next(
        m.message_id for m in container.file_store._messages.values() if m.role == "assistant"
    )


def _do_chat(client: TestClient) -> None:
    client.post("/api/chat/stream", data={"query": "hi"})


def test_feedback_like_ok(test_settings, fake_container, sample_doc):
    fake_container.retriever = FakeRetriever(RetrievalResult(query="q", docs=[sample_doc]))
    fake_container.llm = FakeLLM([StreamDelta(content="ok")])
    app = create_app(settings=test_settings, container=fake_container)

    with TestClient(app) as client:
        _do_chat(client)
        mid = _get_last_assistant_message_id(client, fake_container)
        r = client.post("/api/feedback", json={"message_id": mid, "value": "like"})
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["data"]["feedback_id"].startswith("fb_")
    assert body["data"]["duplicate"] is False


def test_feedback_unknown_message_404(test_settings, fake_container):
    app = create_app(settings=test_settings, container=fake_container)
    with TestClient(app) as client:
        r = client.post("/api/feedback", json={"message_id": "nope", "value": "like"})
    assert r.status_code == 404
    assert r.json()["success"] is False


def test_feedback_duplicate_returns_existing(test_settings, fake_container, sample_doc):
    fake_container.retriever = FakeRetriever(RetrievalResult(query="q", docs=[sample_doc]))
    fake_container.llm = FakeLLM([StreamDelta(content="ok")])
    app = create_app(settings=test_settings, container=fake_container)

    with TestClient(app) as client:
        _do_chat(client)
        mid = _get_last_assistant_message_id(client, fake_container)
        r1 = client.post("/api/feedback", json={"message_id": mid, "value": "like"})
        r2 = client.post("/api/feedback", json={"message_id": mid, "value": "like"})

    assert r1.json()["data"]["duplicate"] is False
    assert r2.json()["data"]["duplicate"] is True
    assert r1.json()["data"]["feedback_id"] == r2.json()["data"]["feedback_id"]


def test_feedback_invalid_value_422(test_settings, fake_container):
    app = create_app(settings=test_settings, container=fake_container)
    with TestClient(app) as client:
        r = client.post("/api/feedback", json={"message_id": "x", "value": "dislike"})
    # Pydantic Literal mismatch → 422
    assert r.status_code == 422
