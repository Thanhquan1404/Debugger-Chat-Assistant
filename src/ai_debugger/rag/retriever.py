"""
Three-stage retriever (D10).

Stage A — vector search on static + dynamic (parallel).
Stage B — hydrate payload from DocStore by doc_id.
Stage C — merge, dedup, sort by score, cut top-N.

Note (Phase 3): dynamic collection is intentionally empty.
The dynamic code path exists for Phase 5 but always returns [].
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Literal

import structlog

from ai_debugger.config import Settings
from ai_debugger.core.embeddings import EmbeddingClient
from ai_debugger.rag.doc_store import DocStore
from ai_debugger.rag.milvus_client import MilvusStore

log = structlog.get_logger(__name__)


SourceKind = Literal["static", "dynamic"]


@dataclass
class RetrievedDoc:
    doc_id: str
    source: SourceKind
    score: float
    # Hydrated payload (from DocStore)
    error_content: str
    system_name: str | None = None
    error_code: str | None = None
    root_cause: str | None = None
    symptoms: list[str] = field(default_factory=list)
    solution_summary: str | None = None
    solution_steps: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    confidence_score: float | None = None       
    weighted_score: float = 0.0                 

    def to_dict(self) -> dict[str, Any]:
        """JSON-safe representation for the `sources` event."""
        out = {
            "doc_id": self.doc_id,
            "source": self.source,
            "score": round(self.score, 4),
            "system_name": self.system_name,
            "error_code": self.error_code,
            "tags": self.tags,
        }
        if self.confidence_score is not None:
            out["confidence_score"] = round(self.confidence_score, 4)

        return out

    def to_context_block(self, index: int) -> str:
        """Render one doc as a block for the prompt's <retrieved_context>."""
        lines = [
            f"[DOC_{index}] doc_id={self.doc_id} | source={self.source} | score={self.score:.3f}",
            f"system: {self.system_name or '(unknown)'}"
            + (f" | error_code: {self.error_code}" if self.error_code else ""),
            f"error: {self.error_content}",
        ]
        if self.symptoms:
            lines.append("symptoms:")
            for s in self.symptoms:
                lines.append(f"  - {s}")
        if self.root_cause:
            lines.append(f"root_cause: {self.root_cause}")
        if self.solution_summary:
            lines.append(f"solution: {self.solution_summary}")
        if self.solution_steps:
            lines.append("steps:")
            for i, step in enumerate(self.solution_steps, 1):
                lines.append(f"  {i}. {step}")
        if self.tags:
            lines.append(f"tags: {', '.join(self.tags)}")
        return "\n".join(lines)


@dataclass
class RetrievalResult:
    query: str
    docs: list[RetrievedDoc]
    static_hits: int = 0
    dynamic_hits: int = 0
    dynamic_only: bool = False                  # NEW
    may_be_hallucinated: bool = False 

    @property
    def is_empty(self) -> bool:
        return not self.docs

    def to_context_block(self) -> str:
        if not self.docs:
            return ""
        blocks = [doc.to_context_block(i) for i, doc in enumerate(self.docs, 1)]
        return "\n---\n".join(blocks)


class Retriever:
    def __init__(
        self,
        settings: Settings,
        milvus: MilvusStore,
        doc_store: DocStore,
        embedder: EmbeddingClient,
        dynamic_store=None,   
    ) -> None:
        self._settings = settings
        self._milvus = milvus
        self._doc_store = doc_store
        self._embedder = embedder
        self._dynamic_store = dynamic_store

    async def retrieve(self, query: str) -> RetrievalResult:
        if not query.strip():
            raise ValueError("query must not be empty")

        # --- Stage A ---
        [query_vec] = await self._embedder.embed([query])

        static_task = asyncio.to_thread(
            self._milvus.search_static, query_vec,
            limit=self._settings.top_k_per_collection,
        )
        dynamic_task = asyncio.to_thread(
            self._milvus.search_dynamic, query_vec,
            limit=self._settings.top_k_per_collection,
        )
        static_hits, dynamic_hits = await asyncio.gather(static_task, dynamic_task)

        thr = self._settings.score_threshold
        static_hits = [h for h in static_hits if h.get("score", 0.0) >= thr]
        dynamic_hits = [h for h in dynamic_hits if h.get("score", 0.0) >= thr]

        # --- Stage B: hydrate static ---
        static_docs: list[RetrievedDoc] = []
        for hit in static_hits:
            doc_id = hit.get("doc_id")
            if not doc_id:
                continue
            doc = self._doc_store.get(doc_id)
            if doc is None:
                log.warning("retriever.orphan_static_hit", doc_id=doc_id)
                continue
            static_docs.append(
                RetrievedDoc(
                    doc_id=doc.doc_id, source="static", score=float(hit["score"]),
                    error_content=doc.error_content, system_name=doc.system_name,
                    error_code=doc.error_code, root_cause=doc.root_cause,
                    symptoms=list(doc.symptoms), solution_summary=doc.solution.summary,
                    solution_steps=list(doc.solution.steps), tags=list(doc.tags),
                )
            )

        # --- Stage B: hydrate dynamic (skipped if no dynamic_store) ---
        dynamic_docs: list[RetrievedDoc] = []
        if self._dynamic_store is not None:
            for hit in dynamic_hits:
                mid = hit.get("memory_id")
                if not mid:
                    continue
                mem = self._dynamic_store.get(mid)
                if mem is None:
                    log.warning("retriever.orphan_dynamic_hit", memory_id=mid)
                    continue
                dynamic_docs.append(
                    RetrievedDoc(
                        doc_id=mem.memory_id, source="dynamic", score=float(hit["score"]),
                        error_content=mem.error_content,
                        solution_summary=mem.llm_verified_solution,
                        tags=list(mem.tags),
                        confidence_score=mem.confidence_score,
                    )
                )

        # --- Stage C: weighted merge + flags ---
        dynamic_only = False
        may_be_hallucinated = False

        if not static_docs and not dynamic_docs:
            pass
        elif static_docs and not dynamic_docs:
            for d in static_docs:
                d.weighted_score = d.score
        elif not static_docs and dynamic_docs:
            dynamic_only = True
            for d in dynamic_docs:
                d.weighted_score = d.score
            min_conf = min((d.confidence_score or 0.0) for d in dynamic_docs)
            if min_conf < self._settings.learning_confidence_protect:
                may_be_hallucinated = True
                log.warning(
                    "retriever.dynamic_only_may_be_hallucinated",
                    min_confidence=min_conf,
                    n_dynamic=len(dynamic_docs),
                )
        else:
            sw = self._settings.static_weight
            dw = self._settings.dynamic_weight
            for d in static_docs:
                d.weighted_score = d.score * sw
            for d in dynamic_docs:
                d.weighted_score = d.score * dw

        merged = static_docs + dynamic_docs
        merged.sort(key=lambda d: d.weighted_score, reverse=True)
        final = merged[: self._settings.top_n_final]

        log.info(
            "retriever.done",
            static_hits=len(static_docs), dynamic_hits=len(dynamic_docs),
            returned=len(final), dynamic_only=dynamic_only,
            may_be_hallucinated=may_be_hallucinated,
        )
        return RetrievalResult(
            query=query, docs=final,
            static_hits=len(static_docs), dynamic_hits=len(dynamic_docs),
            dynamic_only=dynamic_only, may_be_hallucinated=may_be_hallucinated,
        )