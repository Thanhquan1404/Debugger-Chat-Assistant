"""Application configuration (pydantic-settings)."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All settings, loaded from .env / environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- LLM (D1) ---
    llm_endpoint: str = Field(..., alias="LLM_ENDPOINT")
    llm_api_key: SecretStr = Field(..., alias="LLM_API_KEY")
    llm_model: str = Field("gpt-6-luna", alias="LLM_MODEL")
    embedding_model: str = Field("text-embedding-3-small", alias="EMBEDDING_MODEL")
    llm_timeout_seconds: int = Field(60, alias="LLM_TIMEOUT_SECONDS")
    llm_max_retries: int = Field(3, alias="LLM_MAX_RETRIES")

    # --- OCR (D3) ---
    ocr_lang: Literal["en"] = Field("en", alias="OCR_LANG")
    ocr_min_confidence: float = Field(0.5, alias="OCR_MIN_CONFIDENCE")

    # --- App ---
    app_env: Literal["dev", "prod", "test"] = Field("dev", alias="APP_ENV")
    log_level: str = Field("INFO", alias="LOG_LEVEL")
    log_json: bool = Field(False, alias="LOG_JSON")
    max_upload_mb: int = Field(10, alias="MAX_UPLOAD_MB")

    # --- Reserved for Phase 2+ ---
    milvus_uri: str = Field("./data/milvus_data/ai_debugger.db", alias="MILVUS_DB_PATH")
    static_collection: str = Field("static_database", alias="STATIC_COLLECTION")
    dynamic_collection: str = Field("dynamic_database", alias="DYNAMIC_COLLECTION")
    milvus_index_type: str = Field("FLAT", alias="MILVUS_INDEX_TYPE")
    milvus_metric_type: str = Field("COSINE", alias="MILVUS_METRIC_TYPE")
    embedding_batch_size: int = Field(16, alias="EMBEDDING_BATCH_SIZE")
    metadata_dir: Path = Field(Path("./data/metadata"), alias="METADATA_DIR")
    doc_store_dir: Path = Field(Path("./data"), alias="DOC_STORE_DIR")
    dlq_dir: Path = Field(Path("./data/dlq"), alias="DLQ_DIR")
    top_k_per_collection: int = Field(5, alias="TOP_K_PER_COLLECTION")
    top_n_final: int = Field(3, alias="TOP_N_FINAL")
    score_threshold: float = Field(0.30, alias="SCORE_THRESHOLD")
    dedup_threshold: float = Field(0.95, alias="DEDUP_THRESHOLD")
    confidence_min: float = Field(0.80, alias="CONFIDENCE_MIN")
    prompts_dir: Path = Field(Path("./config/prompts"), alias="PROMPTS_DIR")
    sse_heartbeat_seconds: int = Field(60, alias="SSE_HEARTBEAT_SECONDS")
    max_image_bytes: int = Field(10 * 1024 * 1024, alias="MAX_IMAGE_BYTES")
    history_max_turns: int = Field(3, alias="HISTORY_MAX_TURNS")
    serve_static: bool = Field(True, alias="SERVE_STATIC")
    static_dir: Path = Field("./frontend", alias="STATIC_DIR")
    learning_queue_maxsize: int = Field(100, alias="LEARNING_QUEUE_MAXSIZE")
    learning_confidence_ignore: float = Field(0.75, alias="LEARNING_CONFIDENCE_IGNORE")
    learning_confidence_protect: float = Field(0.90, alias="LEARNING_CONFIDENCE_PROTECT")
    static_weight: float = Field(0.7, alias="STATIC_WEIGHT")
    dynamic_weight: float = Field(0.3, alias="DYNAMIC_WEIGHT")

    @field_validator("max_upload_mb")
    @classmethod
    def _positive_upload(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("MAX_UPLOAD_MB must be positive")
        return v

    @field_validator("milvus_index_type")
    @classmethod
    def _valid_index_type(cls, v: str) -> str:
        allowed = {"FLAT", "HNSW", "IVF_FLAT"}
        if v.upper() not in allowed:
            raise ValueError(f"MILVUS_INDEX_TYPE must be one of {allowed}, got {v}")
        return v.upper()

    @field_validator("milvus_metric_type")
    @classmethod
    def _valid_metric_type(cls, v: str) -> str:
        allowed = {"COSINE", "L2", "IP"}
        if v.upper() not in allowed:
            raise ValueError(f"MILVUS_METRIC_TYPE must be one of {allowed}, got {v}")
        return v.upper()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Singleton settings accessor."""
    return Settings()  # type: ignore[call-arg]
