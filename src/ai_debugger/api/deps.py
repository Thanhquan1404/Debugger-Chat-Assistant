"""Application container — instantiates singletons once at startup."""
from __future__ import annotations

import asyncio

import structlog

from ai_debugger.config import Settings
from ai_debugger.core.embeddings import EmbeddingClient
from ai_debugger.core.llm_client import LLMClient
from ai_debugger.core.prompt_loader import PromptLoader
from ai_debugger.learning import DLQ, Extractor, LearningPipeline, LearningWorker
from ai_debugger.ocr.engine import OCREngine
from ai_debugger.rag.doc_store import DocStore
from ai_debugger.rag.dynamic_store import DynamicStore
from ai_debugger.rag.milvus_client import MilvusStore
from ai_debugger.rag.retriever import Retriever
from ai_debugger.storage.file_store import FileStore

log = structlog.get_logger(__name__)


class AppContainer:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

        # --- Retrieval stack ---
        self.milvus = MilvusStore(settings)
        self.doc_store = DocStore(settings.doc_store_dir / "static_store" / "docs.jsonl")
        self.doc_store.load()
        self.dynamic_store = DynamicStore(
            settings.doc_store_dir / "dynamic_store" / "memories.jsonl"
        )
        self.dynamic_store.load()
        self.embedder = EmbeddingClient(settings)
        self.retriever = Retriever(
            settings, self.milvus, self.doc_store, self.embedder, self.dynamic_store
        )

        # --- LLM + prompt ---
        self.llm = LLMClient(settings)
        self.prompt_loader = PromptLoader(settings.prompts_dir)
        self.prompt_loader.validate("system_debug")
        self.prompt_loader.validate("system_extract")

        # --- OCR + storage ---
        self.ocr_engine = OCREngine(settings)
        self.file_store = FileStore(settings.metadata_dir)
        self.file_store.load()

        # --- Learning (Phase 5) ---
        self.dlq = DLQ(settings.dlq_dir / "learning_failures.jsonl")
        self.extractor = Extractor(llm=self.llm, prompt_loader=self.prompt_loader)
        self.learning_pipeline = LearningPipeline(
            settings=settings,
            milvus=self.milvus,
            embedder=self.embedder,
            dynamic_store=self.dynamic_store,
            file_store=self.file_store,
            extractor=self.extractor,
            dlq=self.dlq,
        )
        self.learning_queue: asyncio.Queue = asyncio.Queue(
            maxsize=settings.learning_queue_maxsize
        )
        self.learning_worker = LearningWorker(
            queue=self.learning_queue, pipeline=self.learning_pipeline
        )

        log.info(
            "container.ready",
            static_docs=len(self.doc_store),
            dynamic_memories=len(self.dynamic_store),
        )