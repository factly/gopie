# GoPie Chat Server Test Suite

This directory contains the end-to-end (E2E) and unit tests for the GoPie Chat Server.

## E2E tests (`tests/e2e/`)

What it does:

- Validates chat-completions workflows (single and multi-dataset) end to end
- Verifies schema upload endpoint behavior

How to run:

```bash
uv sync --dev
docker compose -f docker-compose-noauth.yaml up --build
cd chat-server

# All E2E tests
uv run pytest tests/e2e/ -v -n auto

# Specific categories
uv run pytest tests/e2e/test_e2e_script.py::test_single_dataset_cases -v -n auto
uv run pytest tests/e2e/test_e2e_script.py::test_multi_dataset_cases -v -n auto
uv run pytest tests/e2e/test_e2e_script.py::test_all_cases -v -n auto

# Schema upload tests
uv run pytest tests/e2e/test_upload_schema.py -v -n auto

# Disable colorful formatter
uv run pytest tests/e2e/ --disable-formatter -v -n auto
```

## Unit tests (`tests/unit/`)

What it does:

- Checks adapters, providers, vector store, dataset upload, and prompts

How to run:

```bash
uv sync --dev

# All unit tests
uv run pytest tests/unit/ -v -n auto

# Run entire suite
uv run pytest tests/ -v -n auto
```

## Evaluator-based tests

For generator/runner style evaluator tests (including visualization), see `tests/evaluator/README.md`.
