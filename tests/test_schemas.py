from __future__ import annotations

import pytest
from pydantic import ValidationError

from ai_debugger.schemas import DynamicMemory, LearningExtraction, StaticErrorDoc


def test_static_doc_valid(sample_static_doc: dict) -> None:
    doc = StaticErrorDoc.model_validate(sample_static_doc)
    assert doc.doc_id == "UIT_ERR_DOC_1001"
    assert doc.solution.summary
    assert doc.embedding_text() == doc.error_content  # C6


def test_static_doc_missing_required(sample_static_doc: dict) -> None:
    broken = {k: v for k, v in sample_static_doc.items() if k != "solution"}
    with pytest.raises(ValidationError):
        StaticErrorDoc.model_validate(broken)


def test_static_doc_error_content_too_short(sample_static_doc: dict) -> None:
    broken = {**sample_static_doc, "error_content": "x"}
    with pytest.raises(ValidationError):
        StaticErrorDoc.model_validate(broken)


def test_dynamic_memory_valid() -> None:
    mem = DynamicMemory(
        memory_id="DYN_UIT_20261001T000000Z",
        session_id="s-1",
        error_content="503 Service Unavailable khi submit đăng ký môn học",
        user_query_summary="Tại sao bấm đăng ký bị 503?",
        llm_verified_solution="Clear cookie, dùng Incognito.",
        confidence_score=0.9,
        tags=["503", "session"],
    )
    assert mem.embedding_text() == mem.error_content  # C6


def test_dynamic_memory_confidence_out_of_range() -> None:
    with pytest.raises(ValidationError):
        DynamicMemory(
            memory_id="DYN_X",
            error_content="valid error content here",
            llm_verified_solution="fix",
            confidence_score=1.5,
        )


def test_learning_extraction_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        LearningExtraction.model_validate(
            {
                "memory_id": "DYN_1",
                "error_content": "some error content",
                "user_query_summary": "why",
                "llm_verified_solution": "fix",
                "confidence_score": 0.9,
                "tags": [],
                "extra_field": "should fail",
            }
        )


def test_learning_extraction_min_confidence() -> None:
    with pytest.raises(ValidationError):
        LearningExtraction.model_validate(
            {
                "memory_id": "DYN_1",
                "error_content": "some error content",
                "user_query_summary": "why",
                "llm_verified_solution": "fix",
                "confidence_score": 0.8,  # below 0.8
            }
        )
