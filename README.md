# AI Debugging Assistant

RAG-based system that turns error screenshots into debugging answers.
See `document.html` (v3.0) for full architecture.

## Quick start

```bash
# 1. Install
make install

# 2. Configure
cp .env.example .env       # fill LLM_ENDPOINT and LLM_API_KEY

# 3. Run
make dev                    # uvicorn --workers 1
curl http://localhost:8000/health
```

## Smoke tests

```bash
# OCR (needs an image)
python scripts/test_ocr.py path/to/error.png

# LLM text + JSON + embeddings
python scripts/test_llm.py
```

## Tests

```bash
make test                                   # offline
RUN_LLM_TESTS=1 pytest tests/test_llm_client.py   # live LLM
```

## Hard constraints (do not violate)

| ID | Constraint |
|----|-----------|
| C1 | Uploaded images are **never** written to disk. |
| C2 | Metadata goes to JSONL files, never a DB engine. |
| C3 | `uvicorn --workers 1` (Milvus-lite). |
| C4 | RapidOCR English-only. |
| C5 | Dislike never triggers side-effects. |
| C6 | Only `error_content` is embedded. |
| C7 | Every doc is schema-validated before insert. |