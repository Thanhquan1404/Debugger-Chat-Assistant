"""
Extract LearningExtraction from a Liked conversation via LLM JSON mode.

- Uses PromptLoader('system_extract') + LLMClient.chat(output='json').
- Validates via Pydantic.
- memory_id is always code-generated (Q5).
"""
from __future__ import annotations

import json
import time
import uuid

import structlog
from pydantic import ValidationError

from ai_debugger.core.llm_client import LLMClient, LLMError
from ai_debugger.core.prompt_loader import PromptError, PromptLoader
from ai_debugger.schemas import LearningExtraction

log = structlog.get_logger(__name__)


class ExtractionError(RuntimeError):
    pass


def generate_memory_id() -> str:
    return f"DYN_UIT_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}"


class Extractor:
    def __init__(self, *, llm: LLMClient, prompt_loader: PromptLoader) -> None:
        self._llm = llm
        self._prompts = prompt_loader

    async def extract(
        self,
        *,
        user_query: str,
        ocr_text: str,
        assistant_answer: str,
        static_sources: list[str],
    ) -> LearningExtraction:
        try:
            prompt = self._prompts.render(
                "system_extract",
                user_query=user_query or "(không có)",
                ocr_text=ocr_text or "(không có)",
                assistant_answer=assistant_answer or "(không có)",
                static_sources=", ".join(static_sources) if static_sources else "(không có)",
            )
        except PromptError as exc:
            raise ExtractionError(f"prompt render failed: {exc}") from exc

        try:
            raw = await self._llm.chat(prompt.to_messages(), output="json", temperature=0.1)
        except LLMError as exc:
            raise ExtractionError(f"LLM call failed: {exc}") from exc

        try:
            data = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ExtractionError(f"LLM returned non-JSON: {exc}; raw={raw[:200]}") from exc

        if not isinstance(data, dict):
            raise ExtractionError(f"LLM returned non-object JSON: {type(data).__name__}")

        # Q5: always override memory_id with code-generated value
        data["memory_id"] = generate_memory_id()

        try:
            return LearningExtraction.model_validate(data)
        except ValidationError as exc:
            raise ExtractionError(f"schema validation failed: {exc.errors()[0]['msg']}") from exc