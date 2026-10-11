"""Async embeddings client (D9)."""
from __future__ import annotations

import structlog
from openai import APIConnectionError, APIError, APITimeoutError, AsyncOpenAI, RateLimitError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from ai_debugger.config import Settings

log = structlog.get_logger(__name__)

_RETRYABLE = (APIConnectionError, APITimeoutError, RateLimitError, APIError)

EXPECTED_DIM = 1536  # text-embedding-3-small - mofify if you use another


class EmbeddingClient:
    def __init__(self, settings: Settings) -> None:
        self._client = AsyncOpenAI(
            base_url=settings.llm_endpoint,
            api_key=settings.llm_api_key.get_secret_value(),
            timeout=settings.llm_timeout_seconds,
            max_retries=0,
        )
        self._model = settings.embedding_model

    @retry(
        retry=retry_if_exception_type(_RETRYABLE),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Return a list of embeddings, one per input text."""
        if not texts:
            return []
        log.info("embed.request", model=self._model, n=len(texts))
        resp = await self._client.embeddings.create(model=self._model, input=texts)
        vectors = [d.embedding for d in resp.data]
        if vectors and (len(vectors[0]) != EXPECTED_DIM):
            log.warning(
                "embed.unexpected_dim",
                expected=EXPECTED_DIM,
                got=len(vectors[0]),
            )
        log.info("embed.response", n=len(vectors), dim=len(vectors[0]) if vectors else 0)
        return vectors

    async def embed_one(self, text: str) -> list[float]:
        [vec] = await self.embed([text])
        return vec
