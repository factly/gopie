# CLAUDE.md - Chat Server (AI Agent)

This file provides guidance to Claude Code when working with the Python chat server of Gopie.

## Quick Start

```bash
cd chat-server
uv sync
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

## Development Commands

- **Development**: `uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload`
- **Tests**: `pytest` or `uv run pytest`
- **Unit tests only**: `pytest -m unit`
- **E2E tests only**: `pytest -m e2e`
- **Code formatting**: `black .`
- **Import sorting**: `isort .`
- **Install dependencies**: `uv sync`
- **Pre-commit setup**: `pre-commit install`

## Architecture Overview

### AI Agent System (LangGraph)

The chat server is built as a **multi-agent AI system** using LangGraph for orchestrating complex workflows:

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Server                           │
│  ┌─────────────────┐  ┌─────────────────────────────────┐   │
│  │   API Routes    │  │       Middleware               │   │
│  │   (Query/Upload)│  │    (CORS, Timing, Auth)        │   │
│  └─────────────────┘  └─────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                 Agent Workflow Layer                        │
│  ┌─────────────────┐  ┌─────────────────────────────────┐   │
│  │  Main Agent     │  │    Specialized Agents           │   │
│  │  (Supervisor)   │  │ • Single Dataset Agent          │   │
│  │                 │  │ • Multi Dataset Agent           │   │
│  │                 │  │ • Visualization Agent           │   │
│  └─────────────────┘  └─────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                     Tool Layer                              │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────────────┐   │
│  │SQL Query│ │Schema   │ │Python   │ │Dataset          │   │
│  │Executor │ │Retrieval│ │Code Exec│ │Management       │   │
│  └─────────┘ └─────────┘ └─────────┘ └─────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                 Services Layer                              │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────────────┐   │
│  │ Qdrant  │ │  Go API │ │   E2B   │ │    LLM/AI       │   │
│  │ Vector  │ │ Client  │ │Code Env │ │   Providers     │   │
│  │ Store   │ │         │ │         │ │                 │   │
│  └─────────┘ └─────────┘ └─────────┘ └─────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Tech Stack
- **Framework**: FastAPI with async/await support
- **AI Orchestration**: LangGraph for multi-agent workflows
- **LLM Integration**: LangChain with multiple provider support
- **Vector Database**: Qdrant for schema embeddings and search
- **Code Execution**: E2B for secure Python sandboxing
- **Data Models**: Pydantic for type safety and validation
- **Testing**: Pytest with async support
- **Code Quality**: Black, isort, pre-commit hooks

## Project Structure

```
chat-server/
├── app/
│   ├── main.py                          # FastAPI application entry point
│   ├── api/v1/routers/                  # API endpoints
│   │   ├── query.py                     # Main query processing endpoint
│   │   └── dataset_upload.py            # Schema upload endpoint
│   ├── core/                            # Core configuration and utilities
│   │   ├── config.py                    # Pydantic settings management
│   │   ├── log.py                       # Logging configuration
│   │   ├── session.py                   # HTTP client singleton
│   │   └── constants.py                 # Application constants
│   ├── models/                          # Pydantic data models
│   │   ├── query.py                     # Query result models
│   │   ├── schema.py                    # Dataset schema models
│   │   ├── chat.py                      # Chat message models
│   │   └── data.py                      # Data processing models
│   ├── workflow/                        # LangGraph agent workflows
│   │   ├── agent/                       # Main agent orchestration
│   │   │   ├── graph.py                 # Agent graph definition
│   │   │   ├── node/                    # Agent nodes (steps)
│   │   │   └── types.py                 # Agent state types
│   │   ├── graph/                       # Specialized sub-graphs
│   │   │   ├── single_dataset_graph/    # Single dataset processing
│   │   │   ├── multi_dataset_graph/     # Multi dataset processing
│   │   │   └── visualize_data_graph/    # Data visualization
│   │   └── prompts/                     # LLM prompts and templates
│   ├── tool_utils/                      # LangChain tools
│   │   ├── tools/                       # Individual tool implementations
│   │   └── tool_node.py                 # Tool execution utilities
│   ├── services/                        # External service integrations
│   │   ├── qdrant/                      # Vector database operations
│   │   └── gopie/                       # Go API client services
│   └── utils/                           # Utilities and providers
│       ├── providers/                   # LLM and embedding providers
│       ├── model_registry/              # Model selection and routing
│       └── graph_utils/                 # Graph processing utilities
├── tests/                               # Test suite
│   ├── unit/                           # Unit tests
│   ├── e2e/                            # End-to-end tests
│   └── conftest.py                     # Pytest configuration
├── pyproject.toml                      # Project configuration
└── docker-compose.yaml                # Development services
```

## Agent Workflow Architecture

### Main Agent Graph (`app/workflow/agent/graph.py`)

The main agent uses a **state-based workflow** with conditional routing:

1. **Input Validation**: Validates user queries and context
2. **Context Processing**: Processes available datasets and context
3. **Query Routing**: Routes to appropriate specialized agent
4. **Supervisor**: Decides which agent handles the query
5. **Result Generation**: Formats and returns results
6. **Visualization**: Optional chart generation

### Specialized Agents

#### Single Dataset Agent (`app/workflow/graph/single_dataset_graph/`)
- **Purpose**: Handle queries against a single dataset
- **Workflow**: Query processing → SQL generation → Execution → Validation
- **Use Case**: Simple analytical queries on one table

#### Multi Dataset Agent (`app/workflow/graph/multi_dataset_graph/`)
- **Purpose**: Handle complex queries across multiple datasets
- **Workflow**: 
  1. Query analysis and decomposition
  2. Dataset identification
  3. Subquery generation
  4. Parallel execution
  5. Result aggregation
- **Use Case**: JOIN operations, cross-dataset analytics

#### Visualization Agent (`app/workflow/graph/visualize_data_graph/`)
- **Purpose**: Generate charts and visualizations
- **Workflow**: Data preprocessing → Chart type selection → Vega-Lite spec generation
- **Use Case**: Charts, graphs, data visualization

## Tool System

### LangChain Tools (`app/tool_utils/tools/`)

**SQL Execution Tools**:
- `execute_sql_query.py`: Execute SQL against Go API
- `plan_sql_query.py`: Generate SQL from natural language
- `get_table_schema.py`: Retrieve table schema information

**Dataset Management Tools**:
- `list_datasets.py`: Get available datasets
- `result_paths.py`: Handle result routing

**Code Execution Tools**:
- `run_python_code.py`: Execute Python in E2B sandbox

### Tool Categories
- **Data Execution**: SQL query execution
- **Schema Retrieval**: Database schema operations  
- **Code Execution**: Python code running
- **Visualization**: Chart generation

## Vector Search & Schema Management

### Qdrant Integration (`app/services/qdrant/`)

**Schema Vectorization**:
- Table schemas embedded using OpenAI embeddings
- Column descriptions and metadata indexed
- Similarity search for relevant schemas

**Search Operations**:
- `schema_search.py`: Semantic schema search
- `vector_store.py`: Vector similarity operations
- `schema_vectorization.py`: Schema embedding generation

### Schema Models (`app/models/schema.py`)

```python
@dataclass
class DatasetSchema:
    dataset_id: str
    dataset_name: str
    project_id: str
    table_name: str
    columns: list[ColumnSchema]
    description: str | None = None
```

## LLM Provider System

### Multi-Provider Architecture (`app/utils/providers/`)

**Supported Providers**:
- **Portkey**: AI gateway with fallbacks and caching
- **LiteLLM**: Unified interface for multiple providers
- **OpenAI**: Direct OpenAI API integration
- **Cloudflare**: Cloudflare Workers AI
- **OpenRouter**: Access to multiple models
- **Custom**: Self-hosted model endpoints

**Provider Selection**:
- Model registry for automatic provider routing
- Fallback mechanisms for reliability
- Cost and performance optimization

### Model Configuration (`app/utils/model_registry/`)

```python
# Example model selection
ADVANCED_MODEL = "gpt-4o"           # Complex reasoning
BALANCED_MODEL = "gpt-4o-mini"      # General purpose  
FAST_MODEL = "gpt-3.5-turbo"       # Quick responses
```

## Data Models & Type Safety

### Query Models (`app/models/query.py`)

**Core Data Classes**:
- `SqlQueryInfo`: SQL query with results and metadata
- `SubQueryInfo`: Individual subquery tracking
- `QueryResult`: Complete query execution result
- `SingleDatasetQueryResult`: Single dataset query result

**Type Safety**:
- Pydantic models for all API interfaces
- TypedDict for internal data structures
- Dataclasses for business logic objects

## API Design

### FastAPI Endpoints

**Query Processing** (`/api/v1/query`):
```python
POST /chat/query
{
    "query": "Show me sales data for last month",
    "project_id": "uuid",
    "context": {...}
}
```

**Schema Upload** (`/api/v1/upload_schema`):
```python
POST /upload_schema
{
    "dataset_schema": {...},
    "project_id": "uuid"
}
```

### Streaming Responses

- **Server-Sent Events**: Real-time query progress
- **Tool Usage Updates**: Live tool execution feedback
- **Error Streaming**: Immediate error reporting

## Configuration Management

### Environment Variables (`app/core/config.py`)

**Core Settings**:
```bash
# API Configuration
PROJECT_NAME="Gopie Chat Server"
API_V1_STR="/api/v1"
MODE="development"

# LLM Providers
PORTKEY_API_KEY="your-portkey-key"
OPENAI_API_KEY="your-openai-key"
DEFAULT_LLM_MODEL="gpt-4o"

# Vector Database
QDRANT_HOST="localhost"
QDRANT_PORT=6333
QDRANT_COLLECTION="dataset_collection"

# Code Execution
E2B_API_KEY="your-e2b-key"
E2B_TIMEOUT=120

# External Services
GOPIE_API_ENDPOINT="http://localhost:8000"
```

**Provider-Specific Settings**:
- Portkey gateway configuration
- LiteLLM routing rules
- Custom model endpoints
- Authentication credentials

## Testing Strategy

### Unit Tests (`tests/unit/`)
```bash
# Run unit tests only
pytest -m unit

# Test specific components
pytest tests/unit/test_llm_providers.py
pytest tests/unit/test_vector_store.py
```

### E2E Tests (`tests/e2e/`)
```bash
# Run end-to-end tests
pytest -m e2e

# Specific test cases
pytest tests/e2e/test_single_dataset_cases.py
pytest tests/e2e/test_multi_dataset_cases.py
```

**Test Categories**:
- **Unit**: Individual component testing
- **E2E**: Full workflow testing with real services
- **Integration**: Service interaction testing

## Development Patterns

### Adding New Agent Node

1. **Create Node Function** in `app/workflow/agent/node/`
2. **Define State Updates** in `app/workflow/agent/types.py`  
3. **Add to Graph** in `app/workflow/agent/graph.py`
4. **Create Prompts** in `app/workflow/prompts/`
5. **Add Tests** in `tests/unit/` and `tests/e2e/`

### Creating New Tool

```python
from langchain_core.tools import tool

@tool
async def my_custom_tool(param: str) -> dict:
    """
    Tool description for LLM
    
    Args:
        param: Parameter description
        
    Returns:
        Tool result
    """
    # Implementation
    return {"result": "data"}

# Export tool metadata
__tool__ = my_custom_tool
__tool_category__ = "Custom Category"
__should_display_tool__ = True
```

### Adding LLM Provider

1. **Create Provider Class** in `app/utils/providers/llm_providers/`
2. **Implement Base Interface** from `base.py`
3. **Add Configuration** in `app/core/config.py`
4. **Register Provider** in `model_registry/`
5. **Add Tests** for provider functionality

## Performance & Monitoring

### Observability
- **LangSmith**: LLM call tracing and debugging
- **Structured Logging**: JSON logs with context
- **Metrics Collection**: Query performance tracking
- **Error Tracking**: Comprehensive error handling

### Optimization
- **Async Operations**: Non-blocking I/O throughout
- **Connection Pooling**: Efficient resource usage
- **Caching**: LLM response and embedding caching
- **Streaming**: Real-time response delivery

## Security Considerations

### Code Execution Safety
- **E2B Sandboxing**: Isolated Python execution
- **Timeout Controls**: Prevent infinite loops
- **Resource Limits**: Memory and CPU constraints

### API Security
- **Input Validation**: Pydantic model validation
- **SQL Injection Prevention**: Parameterized queries
- **Rate Limiting**: Request throttling
- **CORS Configuration**: Controlled cross-origin access

## Common Development Tasks

### Adding New Prompt Template

1. **Create Prompt File** in `app/workflow/prompts/`
2. **Use Template Variables** for dynamic content
3. **Add Prompt Selector** logic if conditional
4. **Test Prompt** with different inputs
5. **Document Usage** and parameters

### Debugging Agent Workflow

1. **Enable Debug Logging** in configuration
2. **Use LangSmith Tracing** for LLM calls
3. **Check Agent State** at each node
4. **Validate Tool Results** and error handling
5. **Test Isolated Components** before integration

### Vector Store Operations

```python
# Search schemas by query
schemas = await search_schemas(
    user_query="sales data",
    project_ids=["project-1"],
    top_k=5
)

# Upload new schema
await upload_schema_to_qdrant(
    schema=dataset_schema,
    embeddings=embeddings
)
```

## Deployment Considerations

### Docker Setup
- **Multi-stage builds** for optimization
- **Health checks** for service monitoring
- **Environment configuration** via .env files
- **Service dependencies** properly orchestrated

### Production Settings
- **Async workers** for scalability
- **Connection pooling** for databases
- **Caching layers** for performance
- **Monitoring integration** for observability