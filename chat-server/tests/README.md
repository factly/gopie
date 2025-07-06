# Test Suite for GoPie Chat Server

This directory contains tests for the GoPie Chat Server, including unit tests and end-to-end (E2E) tests.

## Test Files Structure

### E2E Test Files

- `tests/e2e/test_e2e_script.py`: Tests chat completion functionality with actual API calls
- `tests/e2e/test_upload_schema.py`: Tests schema upload endpoint functionality
- `tests/e2e/single_dataset_cases.py`: Contains test cases for single dataset queries
- `tests/e2e/multi_dataset_cases.py`: Contains test cases for multi-dataset queries
- `tests/e2e/visualization_cases.py`: Contains test cases for visualization queries

### Unit Test Files

- `tests/unit/test_prompts.py`: Tests the prompt selection and management functionality
- `tests/unit/test_openai_adapters.py`: Tests OpenAI API format adapters for input/output
- `tests/unit/test_vector_store.py`: Tests vector store operations for schema search
- `tests/unit/test_llm_providers.py`: Tests different LLM provider integrations (Portkey, LiteLLM, etc.)
- `tests/unit/test_dataset_upload.py`: Tests dataset schema upload functionality
- `tests/unit/test_embedding_providers.py`: Tests embedding model providers
- `tests/unit/test_model_registry.py`: Tests model registry and selection functionality

## Running Tests

### Running E2E Tests

```bash
# Run chat completion tests
python -m tests.e2e.test_e2e_script

# Run schema upload tests
python -m tests.e2e.test_upload_schema
```

### Running Unit Tests

```bash
# Run all unit tests
pytest tests/unit/

# Run a specific test file
pytest tests/unit/test_prompts.py
```

## PyTest Configuration

The pytest configuration is in the `pyproject.toml` file at the project root:

```toml
[tool.pytest.ini_options]
testpaths = ["tests/e2e", "tests/unit"]
addopts = """
    --tb=short
    --strict-markers
    --durations=5
    -v
"""
pythonpath = ["."]
python_files = ["test_*.py"]
markers = [
  "e2e: marks tests as end-to-end (deselect with '-m \"not e2e\"')",
  "unit: marks tests as unit tests",
  "slow: marks tests as slow (deselect with '-m \"not slow\"')",
]
cache_dir = "tests/.pytest_cache"
```

## Test Details

### E2E Tests

#### `test_e2e_script.py`

This script performs comprehensive end-to-end testing of the chat completion API:

- **Response Evaluation**: Uses LLM-based evaluation to assess response correctness against expected outcomes

The test uses test cases defined in `single_dataset_cases.py` and `multi_dataset_cases.py` to cover a wide range of query scenarios.

#### `test_upload_schema.py`

Tests the schema upload endpoint with real project and dataset IDs:

- **API Request Testing**: Validates proper API request/response handling
- **Success Response Validation**: Checks that successful uploads return `{"success": True}`
- **Error Handling**: Tests error responses for invalid inputs

### Unit Tests

#### `test_prompts.py`

Tests the prompt management system:

- **Prompt Selection**: Tests selecting the right prompt for each workflow node
- **Prompt Formatting**: Tests proper formatting of prompt inputs
- **LangSmith Integration**: Tests fetching prompts from LangSmith
- **Prompt Fallbacks**: Tests fallback behavior when prompt retrieval fails

#### `test_openai_adapters.py`

Tests adapters for OpenAI-compatible API:

- **Input Format Conversion**: Tests converting from OpenAI request format to internal format
- **Output Format Conversion**: Tests converting internal responses to OpenAI response format
- **Tool Calls Handling**: Tests proper formatting of tool calls in responses
- **Streaming Responses**: Tests generating streaming response chunks

#### `test_vector_store.py`

Tests the vector store functionality:

- **Document Addition**: Tests adding documents to the vector store
- **Similarity Search**: Tests searching for similar documents
- **Filter Handling**: Tests applying filters to search results
- **Schema Search**: Tests searching for relevant schemas

#### `test_llm_providers.py`

Tests various LLM provider integrations:

- **Provider Initialization**: Tests initializing different providers
- **Model Creation**: Tests creating models with different configurations
- **Headers/Authentication**: Tests proper authentication with each provider
- **Providers Tested**: Portkey, PortkeySelfHosted, LiteLLM, OpenRouter, Cloudflare, and Custom providers

#### `test_dataset_upload.py`

Tests the dataset schema upload functionality:

- **Schema Upload Flow**: Tests the complete schema upload process
- **Error Handling**: Tests handling of various error conditions
- **API Integration**: Tests integration with the upload endpoint

#### `test_embedding_providers.py`

Tests embedding model providers:

- **Provider Initialization**: Tests initializing different embedding providers
- **Embedding Model Creation**: Tests creating embedding models
- **Providers Tested**: Portkey, PortkeySelfHosted, LiteLLM, OpenAI, and Custom providers

#### `test_model_registry.py`

Tests the model registry and selection system:

- **Model Configuration**: Tests creating model configs with different parameters
- **Provider Selection**: Tests selecting appropriate providers based on configuration
- **Model Selection**: Tests selecting models for different workflow nodes
- **Tool Integration**: Tests integrating tools with models

## Environment Setup for Tests

The tests rely on environment variables for configuration. Create a `.env` file at the root of the project with the following variables:

```
PORTKEY_API_KEY=your_portkey_api_key
GEMINI_VIRTUAL_KEY=your_gemini_virtual_key
```

## Adding New Tests

### Adding E2E Tests

#### For Chat Completion Tests:

1. Add your test case to the appropriate file:

   - `tests/e2e/single_dataset_cases.py` for single dataset queries
   - `tests/e2e/multi_dataset_cases.py` for multi-dataset queries

2. Run with:
   ```bash
   python -m tests.e2e.test_e2e_script
   ```

### Adding Unit Tests

1. Create a file in `tests/unit/` (name starting with `test_`)

2. Use fixtures defined in `tests/unit/conftest.py` for common test setup and resources

3. Run with:
   ```bash
   pytest tests/unit/your_test_file.py
   ```
