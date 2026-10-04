.PHONY: install dev test lint fmt clean run

install:
	uv venv --python 3.11
	uv pip install -e ".[dev]"

dev:
	uvicorn ai_debugger.main:app --reload --port 8000 --workers 1

run:
	uvicorn ai_debugger.main:app --host 0.0.0.0 --port 8000 --workers 1

test:
	pytest -q

lint:
	ruff check src tests scripts

fmt:
	ruff format src tests scripts

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf .pytest_cache .ruff_cache .mypy_cache

init-db:
	python scripts/init_milvus.py

ingest:
	python scripts/ingest_static.py --dir data/static_docs

test-retrieval:
	@if [ -z "$(Q)" ]; then echo "usage: make test-retrieval Q=\"<query>\""; exit 1; fi
	python scripts/test_retrieval.py "$(Q)"

test-pipeline:
	@if [ -z "$(IMG)" ]; then echo "usage: make test-pipeline IMG=path/to/img.png [Q=\"...\"]"; exit 1; fi
	python scripts/test_pipeline.py "$(IMG)" $(if $(Q),--query "$(Q)",)

serve:
	uvicorn ai_debugger.main:app --host 0.0.0.0 --port 8000 --workers 1