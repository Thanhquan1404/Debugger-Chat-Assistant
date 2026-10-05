from __future__ import annotations

import json

import pytest
import yaml

from ai_debugger.core.prompt_loader import PromptLoader
from ai_debugger.learning.extractor import ExtractionError, Extractor, generate_memory_id


class FakeLLM:
    def __init__(self, response: str):
        self._response = response

    async def chat(self, messages, *, output="text", temperature=0.2, max_tokens=None):
        return self._response


@pytest.fixture
def prompt_loader(tmp_path):
    d = tmp_path / "prompts"
    d.mkdir()
    (d / "system_extract.yaml").write_text(
        yaml.safe_dump({
            "name": "system_extract",
            "version": 2,
            "system": "Extract.",
            "user_template": "Q={{ user_query }} O={{ ocr_text }} A={{ assistant_answer }} S={{ static_sources }}",
        }),
        encoding="utf-8",
    )
    return PromptLoader(d)


@pytest.mark.asyncio
async def test_extract_ok(prompt_loader):
    payload = {
        "memory_id": "FROM_LLM_IGNORED",
        "error_content": "503 on dkmh portal",
        "user_query_summary": "why 503",
        "llm_verified_solution": "clear cookie",
        "confidence_score": 0.88,
        "tags": ["503"],
    }
    ex = Extractor(llm=FakeLLM(json.dumps(payload)), prompt_loader=prompt_loader)
    result = await ex.extract(
        user_query="q", ocr_text="o", assistant_answer="a", static_sources=["D1"],
    )
    assert result.error_content == "503 on dkmh portal"
    # memory_id MUST be code-generated, not LLM's
    assert result.memory_id.startswith("DYN_UIT_")


@pytest.mark.asyncio
async def test_extract_rejects_invalid_json(prompt_loader):
    ex = Extractor(llm=FakeLLM("not json at all"), prompt_loader=prompt_loader)
    with pytest.raises(ExtractionError):
        await ex.extract(user_query="q", ocr_text="", assistant_answer="a", static_sources=[])


@pytest.mark.asyncio
async def test_extract_rejects_missing_field(prompt_loader):
    bad = {"error_content": "x", "confidence_score": 0.9}
    ex = Extractor(llm=FakeLLM(json.dumps(bad)), prompt_loader=prompt_loader)
    with pytest.raises(ExtractionError):
        await ex.extract(user_query="q", ocr_text="", assistant_answer="a", static_sources=[])


def test_generate_memory_id_unique():
    ids = {generate_memory_id() for _ in range(20)}
    assert len(ids) == 20