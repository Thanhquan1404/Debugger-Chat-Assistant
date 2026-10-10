"""POST /api/feedback — record a Like and enqueue a learning job."""
from __future__ import annotations

import time
import uuid

from fastapi import APIRouter, HTTPException, Request

from ai_debugger.api.schemas import Envelope, FeedbackRequest
from ai_debugger.learning import LearningJob
from ai_debugger.storage.models import FeedbackRecord

router = APIRouter(prefix="/api", tags=["feedback"])


def _new_feedback_id() -> str:
    return f"fb_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}"


@router.post(
    "/feedback",
    response_model=Envelope,
    summary="Submit feedback (like only)",
    description=(
        "Ghi nhận Like cho một assistant message. Idempotent theo message_id. "
        "Nếu là lần Like đầu, một learning job được xếp vào queue nền."
    ),
)
async def submit_feedback(payload: FeedbackRequest, request: Request) -> Envelope:
    container = request.app.state.container

    msg = container.file_store.get_message(payload.message_id)
    if msg is None:
        raise HTTPException(
            status_code=404,
            detail=f"message_id {payload.message_id!r} không tồn tại.",
        )

    # Idempotent: same message → return existing
    existing = container.file_store.get_feedback(payload.message_id)
    if existing is not None:
        return Envelope(
            data={"feedback_id": existing.feedback_id, "duplicate": True, "queued": False},
            success=True,
        )

    fb = FeedbackRecord(
        feedback_id=_new_feedback_id(),
        message_id=payload.message_id,
        session_id=msg.session_id,
        value=payload.value,
    )
    await container.file_store.append_feedback(fb)

    queued = False
    # Only assistant messages are eligible for learning.
    if msg.role == "assistant":
        user_msg = _find_previous_user_message(container.file_store, msg.session_id, msg.message_id)
        if user_msg is not None and container.learning_worker is not None:
            job = LearningJob(
                feedback_id=fb.feedback_id,
                session_id=msg.session_id,
                user_message_id=user_msg.message_id,
                assistant_message_id=msg.message_id,
            )
            queued = container.learning_worker.enqueue(job)

    return Envelope(
        data={"feedback_id": fb.feedback_id, "duplicate": False, "queued": queued},
        success=True,
    )


def _find_previous_user_message(file_store, session_id: str, before_message_id: str):
    ids = file_store._session_order.get(session_id, [])
    try:
        idx = ids.index(before_message_id)
    except ValueError:
        return None
    for i in range(idx - 1, -1, -1):
        m = file_store._messages.get(ids[i])
        if m is not None and m.role == "user":
            return m
    return None