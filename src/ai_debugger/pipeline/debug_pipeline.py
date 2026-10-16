"""
Main debug pipeline (Q9 = single-shot, Q10 = streaming).

Flow:
  validate(inputs)
    → build labeled query (Q1)
    → retriever.retrieve
    → yield `sources`
    → render prompt
    → llm.stream
    → yield `usage` / `answer_delta` per chunk
    → yield `done` with accumulated answer
"""
from __future__ import annotations

from collections.abc import AsyncIterator

import structlog

from ai_debugger.config import Settings
from ai_debugger.core.llm_client import LLMClient, LLMError
from ai_debugger.core.prompt_loader import PromptError, PromptLoader
from ai_debugger.pipeline.events import StreamEvent
from ai_debugger.rag.retriever import Retriever

log = structlog.get_logger(__name__)


def build_labeled_query(ocr_text: str, user_prompt: str) -> str:
    """
    Q1: combine OCR + user prompt with explicit source labels.
    If only one source is present, still label it.
    """
    parts: list[str] = []
    if ocr_text.strip():
        parts.append(f"[FROM_IMAGE] {ocr_text.strip()}")
    if user_prompt.strip():
        parts.append(f"[FROM_USER] {user_prompt.strip()}")
    return "\n".join(parts)


async def run_debug_pipeline(
    *,
    ocr_text: str,
    user_prompt: str,
    message_id: str,
    settings: Settings,
    retriever: Retriever,
    llm: LLMClient,
    prompt_loader: PromptLoader,
    history: list[dict[str, str]] | None = None,
) -> AsyncIterator[StreamEvent]:
    # ---------- 1. Validate (Q2) ----------
    if not ocr_text.strip() and not user_prompt.strip():
        yield StreamEvent(
            "error",
            {"message": "Cả OCR text và câu hỏi người dùng đều rỗng — từ chối xử lý."},
        )
        return

    # ---------- 2. Retrieval ----------
    query = build_labeled_query(ocr_text, user_prompt)
    try:
        retrieval = await retriever.retrieve(query)
    except Exception as exc:
        log.error("pipeline.retrieval_failed", error=str(exc))
        yield StreamEvent("error", {"message": f"Retrieval failed: {exc}"})
        return

    yield StreamEvent(
        "sources",
        {
            "docs": [d.to_dict() for d in retrieval.docs],
            "is_empty": retrieval.is_empty,
        },
    )

    # ---------- 3. Render prompt ----------
    context_block = retrieval.to_context_block()
    try:
        prompt = prompt_loader.render(
            "system_debug",
            ocr_text=ocr_text.strip() or "(không có)",
            user_prompt=user_prompt.strip() or "(không có)",
            context_block=context_block or "(không có tài liệu liên quan)",
        )
    except PromptError as exc:
        log.error("pipeline.prompt_failed", error=str(exc))
        yield StreamEvent("error", {"message": f"Prompt rendering failed: {exc}"})
        return

    # ---------- 4. Stream LLM ----------
    answer_parts: list[str] = []
    last_usage: dict | None = None
    messages: list[dict[str, str]] = [{"role": "system", "content": prompt.system}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": prompt.user})

    answer_parts: list[str] = []
    last_usage: dict | None = None

    try:
        async for delta in llm.stream(messages):
            if delta.usage is not None:
                last_usage = delta.usage
                yield StreamEvent("usage", {"usage": delta.usage})
            if delta.reasoning:
                # Reserved for future providers exposing reasoning text
                yield StreamEvent("reasoning_delta", {"text": delta.reasoning})
            if delta.content:
                answer_parts.append(delta.content)
                yield StreamEvent("answer_delta", {"text": delta.content})
    except LLMError as exc:
        log.error("pipeline.llm_failed", error=str(exc))
        yield StreamEvent("error", {"message": f"LLM failed: {exc}"})
        return

    full_answer = "".join(answer_parts)
    yield StreamEvent(
        "done",
        {
            "message_id": message_id,
            "answer": full_answer,
            "sources": [d.to_dict() for d in retrieval.docs],
            "usage": last_usage,
        },
    )
