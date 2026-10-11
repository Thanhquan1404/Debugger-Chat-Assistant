"""Async OpenAI-compatible LLM client (D1, D2)."""
from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Any, Literal

import structlog
from openai import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    AsyncOpenAI,
    BadRequestError,
    RateLimitError,
)
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ai_debugger.config import Settings

log = structlog.get_logger(__name__)

Message = dict[str, str]

# Transient errors that justify a retry
_RETRYABLE = (APIConnectionError, APITimeoutError, RateLimitError, APIError)


class LLMError(RuntimeError):
    """Raised when the LLM call fails after retries."""

@dataclass
class StreamDelta:
    """One chunk from a streaming completion."""

    content: str = ""
    reasoning: str | None = None
    usage: dict[str, Any] | None = None
    finish_reason: str | None = None
    is_usage_only: bool = False
    extras: dict[str, Any] = field(default_factory=dict)


class LLMClient:
    """Thin wrapper around AsyncOpenAI with retry + JSON mode support."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = AsyncOpenAI(
            base_url=settings.llm_endpoint,
            api_key=settings.llm_api_key.get_secret_value(),
            timeout=settings.llm_timeout_seconds,
            max_retries=0,  # we handle retries ourselves
        )
        self._model = settings.llm_model

    @retry(
        retry=retry_if_exception_type(_RETRYABLE),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def _create(
        self,
        messages: list[Message],
        *,
        json_mode: bool,
        temperature: float = 1,
        max_tokens: int | None,
    ) -> str:
        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        try:
            # LLM client contacts
            resp = await self._client.chat.completions.create(**kwargs)
        except BadRequestError as exc:
            # Non-retryable — likely model doesn't support JSON mode or bad payload
            log.error("llm.bad_request", error=str(exc), json_mode=json_mode)
            raise LLMError(f"LLM rejected request: {exc}") from exc

        content = resp.choices[0].message.content
        if not content:
            raise LLMError("LLM returned empty content")
        return content

    async def chat(
        self,
        messages: list[Message],
        *,
        output: Literal["text", "json"] = "text",
        temperature: float = 1,
        max_tokens: int | None = None,
    ) -> str:
        """
        Send a chat completion request.

        Args:
            output: "text" for natural language (main chat), "json" for extraction (D2).
        """
        json_mode = output == "json"
        log.info(
            "llm.request",
            model=self._model,
            output=output,
            n_messages=len(messages),
        )
        try:
            content = await self._create(
                messages,
                json_mode=json_mode,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except _RETRYABLE as exc:
            log.error("llm.retry_exhausted", error=str(exc))
            raise LLMError(f"LLM call failed after retries: {exc}") from exc

        log.info("llm.response", model=self._model, chars=len(content))
        return content

    async def stream(
        self,
        messages: list[Message],
        *,
        temperature: float = 1,
        max_tokens: int | None = None,
    ) -> AsyncIterator[StreamDelta]:
        """
        Stream a completion. Yields StreamDelta chunks until the provider
        sends its terminal signal.

        Note (Q_B): gpt-6-luna hides reasoning text but exposes reasoning_tokens
        in usage. We pass usage through faithfully — UI interprets it.
        """
        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
            "stream_options": {"include_usage": True},
        }
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens

        log.info("llm.stream_start", model=self._model, n_messages=len(messages))

        # Some OpenAI-compatible endpoints reject stream_options.
        try:
            stream = await self._client.chat.completions.create(**kwargs)
        except BadRequestError as exc:
            if "stream_options" in str(exc).lower() or "include_usage" in str(exc).lower():
                log.warning("llm.stream_options_unsupported, retrying without")
                kwargs.pop("stream_options", None)
                stream = await self._client.chat.completions.create(**kwargs)
            else:
                raise LLMError(f"LLM stream rejected: {exc}") from exc

        try:
            async for chunk in stream:
                delta_out = self._parse_chunk(chunk)
                if delta_out is not None:
                    yield delta_out
        except (APIConnectionError, APITimeoutError, RateLimitError, APIError) as exc:
            log.error("llm.stream_error", error=str(exc))
            raise LLMError(f"LLM stream failed: {exc}") from exc

        log.info("llm.stream_done", model=self._model)

    @staticmethod
    def _parse_chunk(chunk: Any) -> StreamDelta | None:
        """Normalize a provider chunk into a StreamDelta. Returns None if nothing to emit."""
        # Usage-only terminal chunk (choices is empty)
        if not getattr(chunk, "choices", None):
            usage = _extract_usage(chunk)
            if usage is not None:
                return StreamDelta(usage=usage, is_usage_only=True, finish_reason="stop")
            return None

        choice = chunk.choices[0]
        delta = choice.delta
        content = getattr(delta, "content", None) or ""
        # Defensive: check both common field names for reasoning text
        reasoning = getattr(delta, "reasoning_content", None) or getattr(delta, "reasoning", None)
        finish = choice.finish_reason
        usage = _extract_usage(chunk)

        if not content and not reasoning and usage is None and finish is None:
            return None

        return StreamDelta(
            content=content,
            reasoning=reasoning,
            usage=usage,
            finish_reason=finish,
        )

def _extract_usage(chunk: Any) -> dict[str, Any] | None:
    """Extract usage dict from a chunk, preserving provider extras (latency_checkpoint, …)."""
    usage_obj = getattr(chunk, "usage", None)
    if usage_obj is None:
        return None
    try:
        data = usage_obj.model_dump()
    except Exception:
        return None
    # Preserve non-standard fields the provider may attach
    extra = getattr(usage_obj, "model_extra", None) or {}
    if extra:
        data.update(extra)
    return data



