# GoPie Chat Server Test Suite

Comprehensive test framework for the GoPie Chat Server, including unit tests, end-to-end tests, and AI-powered evaluation.

## Prerequisites

Before running tests, ensure you have:

1. **Python 3.11+** installed
2. **uv** package manager installed ([installation guide](https://github.com/astral-sh/uv))
3. **Docker & Docker Compose** (for E2E tests)
4. **Environment Variables** configured (see [Environment Setup](#environment-setup))

## Test Categories

| Directory            | Purpose                        | Requires Services | Docs                                  |
| -------------------- | ------------------------------ | ----------------- | ------------------------------------- |
| `unit/`              | Component-level tests          | ❌ No             | [README](unit/README.md)              |
| `e2e/`               | End-to-end workflow tests      | ✅ Yes            | [README](e2e/README.md)               |
| `chat_server_tests/` | Golden dataset evaluation      | ✅ Yes            | [README](chat_server_tests/README.md) |
| `dspy/`              | DSPy evaluator optimization    | ❌ No\*           | [README](dspy/README.md)              |
| `performance_tools/` | Run comparison & tracking      | ❌ No             | [README](performance_tools/README.md) |
| `scripts/`           | Helper utilities & data upload | ✅ Yes            | [README](scripts/README.md)           |

_\*DSPy requires `OPENAI_API_KEY` environment variable_

## Environment Setup

### 1. Install Dependencies

```bash
cd chat-server
uv sync --dev
```

### 2. Configure Environment Variables

The test suite uses configurations from `tests/test_config.py`. Most defaults work for local development. For custom setups, you can override via environment variables:

**Required for Unit Tests:** None (all mocked)

**Required for E2E & Evaluation Tests:**

| Variable               | Default                                         | Description           |
| ---------------------- | ----------------------------------------------- | --------------------- |
| `GOPIE_API_URL`        | `http://localhost:8000`                         | Gopie API server URL  |
| `CHAT_SERVER_URL`      | `http://localhost:8001/api/v1/chat/completions` | Chat server endpoint  |
| `S3_ENDPOINT_URL`      | `http://localhost:9000`                         | MinIO/S3 endpoint     |
| `S3_ACCESS_KEY_ID`     | `minioadmin`                                    | S3 access key         |
| `S3_SECRET_ACCESS_KEY` | `minioadmin`                                    | S3 secret key         |
| `GOPIE_USER_ID`        | `system`                                        | Gopie user ID for API |
| `GOPIE_ORG_ID`         | `123`                                           | Gopie organization ID |

**Required for DSPy Evaluation:**

| Variable         | Description                       |
| ---------------- | --------------------------------- |
| `OPENAI_API_KEY` | OpenAI API key for LLM evaluation |

### 3. Start Required Services (for E2E/Evaluation tests)

```bash
# Start local Gopie with all required services
docker compose -f docker-compose-noauth.yaml up -d
```

This starts:

- **Gopie API Server** (port 8000)
- **Chat Server** (port 8003 → internal 8000)
- **Qdrant** (port 6333, 6334)
- **MinIO** (port 9000) - S3-compatible storage (requires separate setup or from main gopie docker-compose)

> **Note:** Ensure MinIO is running and the `gopie` bucket exists. The E2E tests will auto-create the bucket if it doesn't exist.

## Quick Start

```bash
# Install dependencies
uv sync --dev

# Run all unit tests (no services required)
uv run pytest tests/unit/ -v

# Run all E2E tests (services required)
uv run pytest tests/e2e/ -v

# Run all tests with parallel execution
uv run pytest tests/ -v -n auto
```

## Evaluation Workflow

The evaluation workflow is for testing chat server response quality:

```
1. Generate test cases     → python -m tests.chat_server_tests.test_case_generator --project-ids=...
2. Run evaluation          → python -m tests.chat_server_tests.test_case_runner
3. (Optional) Label data   → Open test_case_labeler.html in browser
4. (Optional) Optimize     → python -m tests.dspy.optimize_evaluator
5. Compare runs            → python -m tests.performance_tools.compare_runs compare
```

### Quick Evaluation Example

```bash
# 1. Ensure services are running
docker compose -f docker-compose-noauth.yaml up -d

# 2. Generate test cases from existing project data
python -m tests.chat_server_tests.test_case_generator --project-ids=your-project-id

# 3. Run the evaluation
python -m tests.chat_server_tests.test_case_runner

# 4. View results in tests/chat_server_tests/output/
```

## Metrics

| Metric                | Range   | Description                  |
| --------------------- | ------- | ---------------------------- |
| `score`               | 0-10    | LLM evaluation quality score |
| `request_time`        | seconds | API response latency         |
| `sql_query_count`     | count   | SQL queries generated        |
| `visualization_count` | count   | Visualizations created       |

**Score Thresholds:** 8+ = Pass, 5-7 = Partial, <5 = Fail
