"""SSE frame serializer — wraps every payload in a {data, ts} envelope (Q_B)."""
from __future__ import annotations

import json

from ai_debugger.pipeline import StreamEvent


def format_sse_frame(event: StreamEvent) -> dict[str, str]:
    """Return a dict suitable for sse-starlette's EventSourceResponse."""
    payload = {
        "data": event.data,
        "ts": event.ts,
    }
    return {
        "event": event.type,
        "data": json.dumps(payload, ensure_ascii=False),
    }
