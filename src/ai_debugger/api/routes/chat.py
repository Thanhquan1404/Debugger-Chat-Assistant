"""POST /api/chat/stream — multipart → SSE streaming."""
from __future__ import annotations

import time
import uuid

import structlog
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from sse_starlette.sse import EventSourceResponse

from ai_debugger.api.sse import format_sse_frame
from ai_debugger.pipeline import StreamEvent, run_debug_pipeline
from ai_debugger.storage.models import MessageRecord
from ai_debugger.utils.image import ImageDecodeError, load_image_in_memory

log = structlog.get_logger(__name__)
router = APIRouter(prefix="/api", tags=["chat"])

_ALLOWED_MAGIC = (
    (b"\x89PNG\r\n\x1a\n", "png"),
    (b"\xff\xd8\xff", "jpeg"),
    (b"RIFF", "webp-riff"),  # extra check below
)


def _new_id(prefix: str) -> str:
    return f"{prefix}_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}"


def _validate_magic(data: bytes) -> None:
    if data.startswith(_ALLOWED_MAGIC[0][0]) or data.startswith(_ALLOWED_MAGIC[1][0]):
        return
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return
    raise HTTPException(status_code=400, detail="Ảnh phải là PNG, JPEG hoặc WebP.")


@router.post(
    "/chat/stream",
    summary="Chat (streaming SSE)",
    description=(
        "Gửi ảnh và/hoặc câu hỏi. Trả về text/event-stream, mỗi frame có "
        "`event: <type>` và `data: {\"data\": {...}, \"ts\": <float>}`.\n\n"
        "Event types: `session`, `sources`, `usage`, `answer_delta`, `done`, `error`."
    ),
)
async def chat_stream(
    request: Request,
    query: str = Form("", description="Câu hỏi người dùng (optional)"),
    session_id: str | None = Form(None, description="Session id (optional, server sinh nếu thiếu)"),
    image: UploadFile | None = File(None, description="Ảnh lỗi (PNG/JPG/WebP, ≤ MAX_IMAGE_BYTES)"),
):
    container = request.app.state.container
    settings = container.settings

    query = (query or "").strip()
    has_image = image is not None and bool(getattr(image, "filename", None))

    if not query and not has_image:
        raise HTTPException(
            status_code=400,
            detail="Cần cung cấp ít nhất 1 trong 2: ảnh hoặc câu hỏi.",
        )

    # ---------- OCR (in-memory only — C1) ----------
    ocr_text = ""
    if has_image:
        try:
            data = await image.read()
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Không đọc được ảnh: {exc}") from exc

        if len(data) > settings.max_image_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"Ảnh vượt giới hạn {settings.max_image_bytes // (1024*1024)}MB.",
            )
        _validate_magic(data)

        try:
            arr = load_image_in_memory(data)
            result = container.ocr_engine.extract(arr)
            ocr_text = result.text
        except ImageDecodeError as exc:
            raise HTTPException(status_code=400, detail=f"Ảnh không hợp lệ: {exc}") from exc
        finally:
            del data  # drop bytes asap

    # ---------- session ----------
    sid = (session_id or "").strip() or _new_id("sess")
    await container.file_store.ensure_session(sid)

    # ---------- history (before appending current user message) ----------
    history = container.file_store.get_recent_history(sid, settings.history_max_turns)

    # ---------- persist user message BEFORE streaming ----------
    user_msg = MessageRecord(
        message_id=_new_id("msg"),
        session_id=sid,
        role="user",
        content=query,
        ocr_text=ocr_text or None,
    )
    await container.file_store.append_message(user_msg)

    assistant_message_id = _new_id("msg")

    async def event_stream():
        # 1. session envelope
        payload = f'{{"data":{{"session_id":"{sid}","user_message_id":"{user_msg.message_id}"}},"ts":{time.time()}}}'
        yield {
            "event": "session",
            "data": payload,
        }

        answer_parts: list[str] = []
        # saved = False

        try:
            async for ev in run_debug_pipeline(
                ocr_text=ocr_text,
                user_prompt=query,
                message_id=assistant_message_id,
                settings=settings,
                retriever=container.retriever,
                llm=container.llm,
                prompt_loader=container.prompt_loader,
                history=history,
            ):
                if ev.type == "answer_delta":
                    answer_parts.append(ev.data.get("text", ""))
                elif ev.type == "done":
                    # Persist assistant BEFORE yielding done so feedback can reference it.
                    await container.file_store.append_message(
                        MessageRecord(
                            message_id=assistant_message_id,
                            session_id=sid,
                            role="assistant",
                            content=ev.data.get("answer", ""),
                            sources=ev.data.get("sources", []),
                            usage=ev.data.get("usage"),
                        )
                    )
                    saved = True
                yield format_sse_frame(ev)
        except Exception as exc:
            log.exception("chat.stream_failed")
            err = StreamEvent("error", {"message": str(exc)})
            yield format_sse_frame(err)

    return EventSourceResponse(
        event_stream(),
        ping=settings.sse_heartbeat_seconds,
        headers={"X-Accel-Buffering": "no"},
    )
