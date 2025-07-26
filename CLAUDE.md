# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Web (Next.js frontend)
- **Development**: `cd web && bun install && bun run dev` (includes WASM preparation)
- **Build**: `cd web && bun run build`
- **Lint**: `cd web && bun run lint`
- **Install dependencies**: `cd web && bun install`

### Chat Server (Python/FastAPI)
- **Development**: `cd chat-server && uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload`
- **Tests**: `cd chat-server && pytest` or `uv run pytest`
- **Unit tests only**: `cd chat-server && pytest -m unit`
- **E2E tests only**: `cd chat-server && pytest -m e2e`
- **Code formatting**: `cd chat-server && black .`
- **Import sorting**: `cd chat-server && isort .`
- **Install dependencies**: `cd chat-server && uv sync`

### Server (Go backend)
- **Development**: `cd server && go run main.go serve`
- **Build**: `cd server && go build -o gopie main.go`
- **Tests**: `cd server && go test ./...`
- **Database migrations**: `cd server && goose up`
- **Generate Swagger docs**: `cd server && swag init`
- **Install dependencies**: `cd server && go mod tidy`

### Docker Development
- **Full stack**: `docker-compose up`
- **Without auth**: `docker-compose -f docker-compose-noauth.yaml up`
- **Without auth with running Web separately (useful during web development)**: 
  - Terminal 1: `docker compose -f docker-compose-noauth.yaml up $(docker compose -f docker-compose-noauth.yaml config --services | grep -v '^gopie-web$' | tr '\n' ' ') --build`
  - Terminal 2: `cd web && bun install && bun run dev`
- **Chat server only**: `cd chat-server && docker-compose up`

## Architecture Overview

Gopie is a multi-dataset SQL agent platform with three main components:

### 1. Web Frontend (`/web`)
- **Framework**: Next.js 15 with React 19, TypeScript
- **Styling**: TailwindCSS with Radix UI components
- **State Management**: Zustand for global state, React Query for server state
- **Key Features**: 
  - DuckDB WASM integration for client-side SQL execution
  - Monaco Editor for SQL editing
  - Chart visualization with Vega-Lite
  - LiveKit integration for voice interactions
  - Zitadel authentication

### 2. Chat Server (`/chat-server`)
- **Framework**: FastAPI with Python 3.11+, managed by uv
- **AI/ML Stack**: LangChain, LangGraph for agent workflows
- **Vector Storage**: Qdrant for schema embeddings and search
- **Key Components**:
  - **Workflow**: LangGraph-based agent system in `app/workflow/`
  - **Tools**: SQL execution, schema retrieval, Python code execution in `app/tool_utils/`
  - **Services**: Qdrant vector operations, dataset management
  - **Models**: Chat, data, query models with Pydantic

### 3. Go Backend Server (`/server`)
- **Framework**: Fiber (Go web framework)
- **Database**: PostgreSQL with SQLC for type-safe queries
- **Storage**: S3-compatible (MinIO) for dataset files
- **OLAP**: DuckDB integration for analytical queries
- **Auth**: Zitadel integration with JWT
- **Key Structure**:
  - **Domain**: Business logic and models
  - **Infrastructure**: Database, S3, external service integrations
  - **Interfaces**: HTTP handlers and middleware
  - **Application**: Services and repositories

## Database Schema

### PostgreSQL (metadata)
- Projects, datasets, chats, database sources
- User management and authentication
- Migrations in `server/infrastructure/postgres/migrations/`

### DuckDB (analytics)
- OLAP workloads and data analysis
- Client-side execution via WASM in web frontend
- Server-side execution for large datasets

### Qdrant (vector storage)
- Schema embeddings for semantic search
- Column descriptions and metadata vectorization

## Key Integration Points

### Authentication Flow
1. Zitadel handles user authentication
2. Go server validates JWT tokens
3. Web frontend manages auth state
4. Chat server receives user context via API

### Data Pipeline
1. Users upload datasets via web frontend
2. Go server processes and stores metadata in PostgreSQL
3. Chat server indexes schema information in Qdrant
4. DuckDB handles analytical queries on actual data

### Agent Workflow
1. User queries processed by chat server's LangGraph agents
2. Schema search via Qdrant vector similarity
3. SQL generation and execution via tools
4. Results formatted and returned to frontend

## Environment Configuration

### Required Environment Files
- `.env` - Main configuration (copy from `.env.example`)
- `config-noauth.env` - No-auth development setup
- `zitadel/key.json` - Zitadel service account key

### Key Services
- **Web**: http://localhost:3000
- **Go Server**: http://localhost:8000
- **Chat Server**: http://localhost:8001
- **PostgreSQL**: localhost:5432
- **Qdrant**: http://localhost:6333
- **MinIO**: http://localhost:9000
- **Zitadel**: http://localhost:4455

## Development Workflow

1. **Database Setup**: Start PostgreSQL and run migrations
2. **Vector Store**: Start Qdrant for schema embeddings
3. **Backend Services**: Start Go server and chat server
4. **Frontend**: Start Next.js development server
5. **Authentication**: Configure Zitadel or use no-auth mode to skip authentication

## Testing Strategy

### Chat Server Tests
- **Unit tests**: Individual component testing
- **E2E tests**: Full workflow testing with real services
- **Test markers**: Use `-m unit` or `-m e2e` to run specific test types

### Integration Testing
- Docker Compose setup for full stack testing
- Test data in `scripts/starter-project/datasets/`

### Sample datasets
- Sample datasets for tests in different formats are available in `datasets/`
