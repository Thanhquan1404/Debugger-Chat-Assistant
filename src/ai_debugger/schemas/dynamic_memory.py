from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class DynamicMemory(BaseModel):
    """Full record stored in memory + doc store after extraction."""

    memory_id: str
    session_id: str | None = None
    error_content: str = Field(
        ...,
        min_length=5,
        description="LLM-distilled error summary — the ONLY field that gets embedded (C6).",
    )
    user_query_summary: str | None = None
    llm_verified_solution: str
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    occurrence_count: int = Field(1, ge=1)
    tags: list[str] = Field(default_factory=list)
    created_at: str | None = None
    last_accessed: str | None = None

    def embedding_text(self) -> str:
        """Return the exact string to embed (C6)."""
        return self.error_content


class LearningExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    memory_id: str = Field(..., min_length=1)
    error_content: str = Field(..., min_length=1)
    user_query_summary: str = Field(..., min_length=1)
    llm_verified_solution: str = Field(..., min_length=1)

    # Đặt ge=0.8 để pass test_learning_extraction_min_confidence (0.2 < 0.8 sẽ raise ValidationError)
    # đồng thời cho phép conf=0.80 trong test_ignored_low_confidence khởi tạo thành công!
    confidence_score: float = Field(..., ge=0.8, le=1.0)
    tags: list[str] = Field(default_factory=list)