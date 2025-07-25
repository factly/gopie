# GoPie Chat Server Test Suite

Comprehensive testing framework for the GoPie Chat Server, featuring end-to-end (E2E) and unit tests for the multi-dataset SQL agent.

## 📁 Test Structure

### E2E Tests (`tests/e2e/`)

**Core Files:**

- `test_e2e_script.py` - Main pytest runner with async test execution
- `test_utils.py` - Utilities for API calls, response processing, and LLM-based evaluation
- `terminal_formatter.py` - Rich terminal output formatter with colors and progress tracking
- `test_upload_schema.py` - Schema upload endpoint testing

**Test Cases:**

- `dataset_test_cases.py` - Single and multi-dataset query test cases
- `visualization_cases.py` - Visualization generation and modification test cases

### Unit Tests (`tests/unit/`)

- `test_dataset_upload.py` - Dataset schema upload/delete API endpoints
- `test_prompts.py` - Prompt management, LangSmith integration, and fallbacks
- `test_vector_store.py` - Qdrant vector operations and schema search
- `test_llm_providers.py` - LLM provider integrations (Portkey, LiteLLM, etc.)
- `test_embedding_providers.py` - Embedding model provider configurations
- `test_model_registry.py` - Model selection and configuration management
- `test_openai_adapters.py` - OpenAI API format conversion utilities

## 🚀 Quick Start

### Prerequisites

```bash
# Install dependencies
uv sync --dev

# Set environment variables
export PORTKEY_API_KEY="your_portkey_api_key"
export PORTKEY_PROVIDER_NAME="openai"  # or your preferred provider
```

### Running Tests

**E2E Tests:**

```bash
# All E2E tests
pytest tests/e2e/ -v

# Specific test categories
pytest tests/e2e/test_e2e_script.py::test_single_dataset_cases -v
pytest tests/e2e/test_e2e_script.py::test_multi_dataset_cases -v
pytest tests/e2e/test_e2e_script.py::test_visualization_cases -v

# All categories combined
pytest tests/e2e/test_e2e_script.py::test_all_cases -v

# Schema upload tests
pytest tests/e2e/test_upload_schema.py -v

# Disable colored terminal output
pytest tests/e2e/ --disable-formatter -v
```

**Unit Tests:**

```bash
# All unit tests
pytest tests/unit/ -v

# Specific components
pytest tests/unit/test_prompts.py -v
pytest tests/unit/test_vector_store.py -v
pytest tests/unit/test_llm_providers.py -v
```

**Combined:**

```bash
# Run everything
pytest tests/ -v

# Run with parallel execution
pytest tests/ -n auto -v
```

## 🧪 Test Details

### E2E Testing Framework

**Architecture:**

- **Async Test Execution**: Built with pytest-asyncio for concurrent testing
- **LLM-Based Evaluation**: Uses GPT-4 to evaluate response quality and correctness
- **Streaming Response Handling**: Processes real-time API responses with tool calls
- **Rich Terminal Output**: Color-coded progress, summaries, and detailed failure reports

**Test Categories:**

1. **Single Dataset Tests** (`SINGLE_DATASET_TEST_CASES`)

   - 20+ test cases covering individual dataset queries
   - Tests for CSR data, election data, and visualization requests
   - Edge cases: empty queries, malicious inputs, division by zero

2. **Multi Dataset Tests** (`MULTI_DATASET_TEST_CASES`)

   - Complex queries requiring multiple dataset integration
   - Tests graph traversal through dataset identification → query planning → execution
   - Error handling: invalid dataset IDs, incompatible joins, resource limits

3. **Visualization Tests** (`VISUALIZATION_TEST_CASES`)
   - Chart generation from previous query results
   - Chart modification (bar → pie, grouped → stacked)
   - Single-request data + visualization workflows

**Response Evaluation:**

```python
{
    "ai_response": "Generated text response",
    "datasets_used": ["dataset_id_1", "dataset_id_2"],
    "sql_queries_generated": ["SELECT * FROM..."],
    "processing_steps": ["Step descriptions"],
    "visualization_results": ["Chart configs"],
    "metadata": {"dataset_count": 2, "sql_query_count": 1}
}
```

### Unit Testing Components

**Core Areas:**

1. **Prompt Management** (`test_prompts.py`)

   - LangSmith integration with fallback mechanisms
   - Prompt formatting and parameter injection
   - Dynamic prompt selection by workflow node

2. **Vector Operations** (`test_vector_store.py`)

   - Qdrant document addition and similarity search
   - Schema search with project/dataset filtering
   - Error handling and fallback behaviors

3. **Provider Integrations** (`test_llm_providers.py`, `test_embedding_providers.py`)

   - Multiple LLM providers: Portkey, LiteLLM, OpenRouter, Cloudflare
   - Authentication and header management
   - Model initialization and configuration

4. **API Adapters** (`test_openai_adapters.py`)

   - OpenAI-compatible request/response formatting
   - Tool call serialization and streaming responses
   - Format conversion utilities

5. **Dataset Management** (`test_dataset_upload.py`)
   - Schema upload/delete operations
   - Error handling for invalid datasets
   - Vector store integration testing

## ⚙️ Configuration

**pytest.ini Options** (in `pyproject.toml`):

```toml
[tool.pytest.ini_options]
testpaths = ["tests/e2e", "tests/unit"]
addopts = "--tb=short --strict-markers --durations=5 -v"
pythonpath = ["."]
python_files = ["test_*.py"]
asyncio_mode = "auto"
markers = [
  "e2e: marks tests as end-to-end",
  "unit: marks tests as unit tests",
  "slow: marks tests as slow"
]
cache_dir = "tests/.pytest_cache"
```

**Test Fixtures** (`conftest.py`):

- `sample_metadata` - Test user/trace/chat IDs
- `mock_settings` - Configuration mocks for all providers
- `mock_vector_store` - Qdrant vector store mocks
- `sample_dataset_schema` - Standard dataset structure
- `sample_query_request` - API request templates

**E2E Test Configuration**:

- Server URL: `http://localhost:8001/api/v1/chat/completions`
- Request timeout: 120 seconds
- Streaming response processing
- LLM evaluation with GPT-4o

## 🛠 Development

### Adding New Tests

**E2E Tests:**

1. Add test cases to `dataset_test_cases.py`:

   ```python
   {
       "messages": [{"role": "user", "content": "Your query"}],
       "model": "test",
       "user": "test",
       "metadata": {"dataset_id": "your_dataset_id"},
       "stream": True,
       "expected_result": "Description of expected behavior"
   }
   ```

2. Run specific test:
   ```bash
   pytest tests/e2e/test_e2e_script.py::test_single_dataset_cases -v
   ```

**Unit Tests:**

1. Create `test_*.py` file in `tests/unit/`
2. Use fixtures from `conftest.py`
3. Follow async/await patterns for database operations
4. Mock external dependencies (API calls, databases)

### Debugging

**E2E Test Debugging:**

```bash
# Run with detailed output
pytest tests/e2e/ -v -s --tb=long

# Single test with no formatter
pytest tests/e2e/test_e2e_script.py::test_single_dataset_cases --disable-formatter -v

# Check specific test case
pytest tests/e2e/ -k "test_name" -v
```

**Unit Test Debugging:**

```bash
# Show print statements
pytest tests/unit/ -s -v

# Stop on first failure
pytest tests/unit/ -x -v

# Run failed tests from last run
pytest tests/unit/ --lf -v
```

## 📊 Test Metrics

**Coverage Areas:**

- ✅ Multi-dataset query processing
- ✅ SQL query generation and execution
- ✅ Visualization generation and modification
- ✅ Vector store operations and schema search
- ✅ LLM provider integrations
- ✅ API format conversions
- ✅ Error handling and edge cases
- ✅ Prompt management and fallbacks

**Performance:**

- E2E tests: ~12-14 minutes for full suite
- Unit tests: ~10 seconds for full suite

Run `pytest --durations=10` to see slowest tests.
