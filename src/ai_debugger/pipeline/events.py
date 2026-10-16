"""Streaming event schema for the debug pipeline."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Literal

EventType = Literal[
    "sources",
    "reasoning_delta",  # reserved — not emitted by Phase 3 (reasoning hidden)
    "answer_delta",
    "usage",
    "done",
    "error",
]


@dataclass
class StreamEvent:
    type: EventType
    data: dict[str, Any] = field(default_factory=dict)
    ts: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type, "ts": self.ts, **self.data}
