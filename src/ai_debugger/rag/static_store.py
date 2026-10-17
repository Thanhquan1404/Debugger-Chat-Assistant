"""
Static ingest pipeline.

Flow (per input .jsonl file):
  1. Read all lines → validate Pydantic (C7). Fail fast on any invalid line.
  2. Detect duplicate doc_id inside the batch → fail.
  3. Diff against current DocStore:
     - doc_id not present → FULL INSERT (embed + Milvus upsert + doc_store append)
     - doc_id present, error_content unchanged → PAYLOAD-ONLY UPDATE (doc_store append only)
     - doc_id present, error_content changed -> FULL RE-EMBED [Q5 = (b)]
  4. Return report.

Never touches solution/symptoms/root_cause for embedding (C6).
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path

import structlog
from pydantic import ValidationError

from ai_debugger.config import Settings
from ai_debugger.core.embeddings import EmbeddingClient
from ai_debugger.rag.doc_store import DocStore
from ai_debugger.rag.milvus_client import MilvusStore
from ai_debugger.schemas import StaticErrorDoc
from ai_debugger.utils.text import normalize_whitespace

log = structlog.get_logger(__name__)


# ---------- report ----------


@dataclass
class IngestReport:
    files_scanned: int = 0
    docs_validated: int = 0
    inserted: int = 0
    updated_payload_only: int = 0
    updated_reembedded: int = 0
    skipped_unchanged: int = 0
    errors: list[str] = field(default_factory=list)

    def summary(self) -> str:
        return (
            f"files={self.files_scanned} validated={self.docs_validated} "
            f"inserted={self.inserted} "
            f"payload_only={self.updated_payload_only} "
            f"reembedded={self.updated_reembedded} "
            f"skipped={self.skipped_unchanged} "
            f"errors={len(self.errors)}"
        )


# ---------- helpers ----------


def _load_jsonl(path: Path) -> list[dict]:
    """Read all JSON objects from a .jsonl file. Raises on syntax error."""
    import json

    rows: list[dict] = []
    with path.open("r", encoding="utf-8-sig") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path.name}:{lineno} invalid JSON: {exc}") from exc
    return rows


def _normalize_error_content(s: str) -> str:
    """Used for equality checks — ignore whitespace drift."""
    return normalize_whitespace(s)


# ---------- main entry ----------


async def ingest_static_docs(
    *,
    input_dir: Path,
    settings: Settings,
    milvus: MilvusStore,
    doc_store: DocStore,
    embedder: EmbeddingClient,
) -> IngestReport:
    report = IngestReport()

    jsonl_files = sorted(input_dir.glob("*.jsonl"))
    report.files_scanned = len(jsonl_files)
    if not jsonl_files:
        log.warning("ingest.no_files", dir=str(input_dir))
        return report

    # 1. Load + validate everything first
    validated: list[StaticErrorDoc] = []
    seen_ids: set[str] = set()
    for path in jsonl_files:
        try:
            rows = _load_jsonl(path)
        except ValueError as exc:
            report.errors.append(str(exc))
            continue
        for idx, row in enumerate(rows, 1):
            try:
                doc = StaticErrorDoc.model_validate(row)
            except ValidationError as exc:
                report.errors.append(f"{path.name}#{idx}: {exc.errors()[0]['msg']}")
                continue
            if doc.doc_id in seen_ids:
                report.errors.append(f"{path.name}#{idx}: duplicate doc_id {doc.doc_id!r}")
                continue
            seen_ids.add(doc.doc_id)
            validated.append(doc)

    report.docs_validated = len(validated)

    if report.errors:
        # Fail fast: do not ingest anything if validation had any error.
        log.error("ingest.validation_failed", n_errors=len(report.errors))
        return report

    # 2. Diff against doc_store
    to_insert: list[StaticErrorDoc] = []       # full pipeline
    to_reembed: list[StaticErrorDoc] = []      # error_content changed
    payload_only: list[StaticErrorDoc] = []    # only solution/other fields changed
    unchanged: list[StaticErrorDoc] = []

    for doc in validated:
        existing = doc_store.get(doc.doc_id)
        if existing is None:
            to_insert.append(doc)
            continue
        norm_existing = _normalize_error_content(existing.error_content)
        norm_incoming = _normalize_error_content(doc.error_content)
        if norm_existing == norm_incoming:
            # vector unchanged → only write payload
            if existing.model_dump() == doc.model_dump():
                unchanged.append(doc)
            else:
                payload_only.append(doc)
        else:
            to_reembed.append(doc)

    log.info(
        "ingest.diff",
        insert=len(to_insert),
        reembed=len(to_reembed),
        payload_only=len(payload_only),
        unchanged=len(unchanged),
    )

    # 3. Embed (batched) — only for insert + reembed
    embed_jobs = to_insert + to_reembed
    vectors: dict[str, list[float]] = {}
    if embed_jobs:
        texts = [d.embedding_text() for d in embed_jobs]
        all_vecs = await _embed_in_batches(embedder, texts, settings.embedding_batch_size)
        for d, vec in zip(embed_jobs, all_vecs, strict=True):
            vectors[d.doc_id] = vec

    # 4. Milvus upsert (insert + reembed)
    milvus_rows = [_to_milvus_row(d, vectors[d.doc_id]) for d in embed_jobs]
    if milvus_rows:
        await asyncio.to_thread(milvus.upsert_static, milvus_rows)

    # 5. Doc store append (all changes; unchanged gets skipped)
    append_docs = to_insert + to_reembed + payload_only
    if append_docs:
        await doc_store.append_many(append_docs)

    # 6. Fill report
    report.inserted = len(to_insert)
    report.updated_reembedded = len(to_reembed)
    report.updated_payload_only = len(payload_only)
    report.skipped_unchanged = len(unchanged)

    log.info("ingest.done", summary=report.summary())
    return report


async def _embed_in_batches(
    embedder: EmbeddingClient,
    texts: list[str],
    batch_size: int,
) -> list[list[float]]:
    out: list[list[float]] = []
    for i in range(0, len(texts), batch_size):
        chunk = texts[i : i + batch_size]
        out.extend(await embedder.embed(chunk))
    return out


def _to_milvus_row(doc: StaticErrorDoc, vector: list[float]) -> dict:
    """Project a StaticErrorDoc into the Milvus row shape (D10 — no payload here)."""
    return {
        "doc_id": doc.doc_id,
        "vector": vector,
        "system_name": doc.system_name,
        "error_code": doc.error_code or "",
        "tags": doc.tags,
        "verified": bool(doc.metadata.verified) if doc.metadata else False,
    }
