# Gopie Chat Server

AI Agent for data analysis using LangGraph, LangChain, and FastAPI.

## Quick Start

```bash
cd chat-server
uv sync
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

## Development Commands

| Command | Description |
|---------|-------------|
| `uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload` | Start development server |
| `pytest` | Run all tests |
| `pytest -m unit` | Run unit tests only |
| `pytest -m e2e` | Run E2E tests only |
| `black .` | Code formatting |
| `isort .` | Import sorting |
| `uv sync` | Install dependencies |

## Configuration

### Environment Variables

#### OLAP Backend Configuration

The chat server supports multiple OLAP backends through the `CHAT_OLAP_DB_TYPE` environment variable:

| Value | Description |
|-------|-------------|
| `duckdb` | DuckDB (default) |
| `motherduck` | MotherDuck cloud DuckDB |
| `motherduck_org` | MotherDuck organization mode |
| `clickhouse` | ClickHouse single-node |
| `clickhouse_cluster` | ClickHouse cluster mode |
| `clickhouse_org` | ClickHouse organization mode |

Example:
```bash
export CHAT_OLAP_DB_TYPE=clickhouse
```

The OLAP backend type controls:
- SQL dialect used in generated queries (sampling syntax, function names)
- System table queries for table metadata
- Fuzzy string matching functions (`levenshtein` vs `levenshteinDistance`)
- LLM prompts for database-aware SQL generation

#### Other Configuration

See `app/core/config.py` for complete configuration options:

```bash
# API Configuration
PROJECT_NAME="Gopie Chat Server"
API_V1_STR="/api/v1"
MODE="development"

# LLM Providers
PORTKEY_API_KEY="your-portkey-key"
OPENAI_API_KEY="your-openai-key"
DEFAULT_LLM_MODEL="gpt-4o"

# Vector Database (Qdrant)
QDRANT_HOST="localhost"
QDRANT_PORT=6333
QDRANT_COLLECTION="dataset_collection"

# Code Execution (E2B)
E2B_API_KEY="your-e2b-key"
E2B_TIMEOUT=120

# External Services
GOPIE_API_ENDPOINT="http://localhost:8000"
```

## Architecture

### OLAP Query Builder

The chat server uses an abstraction layer for database-specific SQL generation:

```
┌─────────────────────────────────────────┐
│   Business Logic (table_utils, etc.)    │
└────────────────────┬────────────────────┘
                     │
┌────────────────────▼────────────────────┐
│    OlapQueryBuilder (Abstract Base)     │
│  - get_estimated_size_query()           │
│  - build_sample_query()                 │
│  - build_levenshtein_query()            │
│  - get_db_type()                        │
└────────────────────┬────────────────────┘
                     │
        ┌────────────┴────────────┐
        ▼                         ▼
   DuckDBQueryBuilder    ClickHouseQueryBuilder
```

#### SQL Syntax Differences

| Feature | DuckDB | ClickHouse |
|---------|--------|------------|
| Table Stats | `duckdb_tables()` | `system.tables` |
| Row Count Column | `estimated_size` | `total_rows` |
| Sampling | `USING SAMPLE X% (system)` | `ORDER BY rand() LIMIT n` |
| Fuzzy Match | `levenshtein()` | `levenshteinDistance()` |
| Random | `random()` | `rand()` |

### Key Components

- **`app/utils/olap/`** - OLAP query builder abstraction
  - `base.py` - Abstract base class
  - `duckdb.py` - DuckDB implementation
  - `clickhouse.py` - ClickHouse implementation
  - `factory.py` - Factory function

- **`app/workflow/`** - LangGraph agent workflows
- **`app/tool_utils/`** - LangChain tools for SQL execution
- **`app/services/`** - External service integrations

## Testing

### Running Tests

```bash
# All tests
pytest

# Unit tests only
pytest -m unit

# E2E tests only
pytest -m e2e

# Specific test file
pytest tests/unit/test_olap_query_builders.py -v
```

### Test Structure

```
tests/
├── unit/                          # Unit tests
│   └── test_olap_query_builders.py  # OLAP query builder tests
├── e2e/                           # End-to-end tests
└── conftest.py                    # Pytest configuration
```

## Docker

```bash
# Start chat server only
docker-compose up

# Full stack (with Go server, Qdrant, etc.)
cd .. && docker-compose -f docker-compose-noauth.yaml up
```
