# CLAUDE.md - Server Backend

This file provides guidance to Claude Code when working with the Go backend server of Gopie.

## Quick Start

```bash
cd server
go mod tidy
go run main.go serve
```

## Development Commands

- **Development**: `go run main.go serve`
- **Build**: `go build -o gopie main.go`
- **Tests**: `go test ./...`
- **Database migrations**: `goose up`
- **Generate Swagger docs**: `swag init`
- **Install dependencies**: `go mod tidy`
- **Database migration Docker**: `docker build -f Dockerfile.migrate -t gopie-migrate . && docker run gopie-migrate`
- **Reindex schemas**: `go run main.go reindex-schemas`

## Architecture Overview

### Hexagonal Architecture (Ports & Adapters)

The server follows **Hexagonal Architecture** principles with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                    Interfaces Layer                         │
│  ┌─────────────────┐  ┌─────────────────────────────────┐   │
│  │   HTTP Routes   │  │       Middleware               │   │
│  │   (REST API)    │  │   (Auth, Validation, Limits)   │   │
│  └─────────────────┘  └─────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                   Application Layer                         │
│  ┌─────────────────┐  ┌─────────────────────────────────┐   │
│  │    Services     │  │       Repositories              │   │
│  │  (Business      │  │      (Interfaces)               │   │
│  │   Logic)        │  │                                 │   │
│  └─────────────────┘  └─────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                     Domain Layer                            │
│  ┌─────────────────┐  ┌─────────────────────────────────┐   │
│  │     Models      │  │       Commands                  │   │
│  │  (Core Entities)│  │    (CLI Interface)              │   │
│  └─────────────────┘  └─────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                 Infrastructure Layer                        │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────────────┐   │
│  │PostgreSQL│ │ DuckDB  │ │   S3    │ │   External APIs │   │
│  │  Store   │ │  OLAP   │ │ Storage │ │ (Zitadel, AI)   │   │
│  └─────────┘ └─────────┘ └─────────┘ └─────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Tech Stack
- **Framework**: Fiber (Go web framework)
- **Database**: PostgreSQL with SQLC for type-safe queries
- **OLAP**: DuckDB for analytical queries  
- **Storage**: S3-compatible (MinIO) for dataset files
- **Auth**: Zitadel integration with JWT tokens
- **CLI**: Cobra for command-line interface
- **Documentation**: Swagger/OpenAPI with Swaggo
- **Logging**: Uber Zap structured logging

## Project Structure

```
server/
├── main.go                          # Application entry point
├── domain/                          # Domain Layer (Core Business Logic)
│   ├── cmd/                        # CLI commands (Cobra)
│   │   ├── root.go                 # Root command configuration
│   │   ├── serve.go                # HTTP server command
│   │   └── reindex_schemas.go      # Schema reindexing command
│   ├── models/                     # Domain entities and DTOs
│   │   ├── project.go              # Project domain models
│   │   ├── dataset.go              # Dataset domain models
│   │   ├── chat.go                 # Chat domain models
│   │   └── ...                     # Other domain models
│   ├── pkg/                        # Domain utilities
│   │   ├── config/                 # Configuration management
│   │   ├── logger/                 # Logging utilities
│   │   └── crypto/                 # Cryptographic utilities
│   └── error.go                    # Domain error definitions
├── application/                     # Application Layer (Use Cases)
│   ├── services/                   # Business logic services
│   │   ├── store.go                # Project/Dataset services
│   │   ├── chat.go                 # Chat management services
│   │   ├── olap.go                 # Analytics services
│   │   └── ai.go                   # AI integration services
│   └── repositories/               # Repository interfaces (ports)
│       ├── store.go                # Data store interfaces
│       ├── olap.go                 # OLAP interfaces
│       └── ai.go                   # AI service interfaces
├── interfaces/                      # Interface Layer (Adapters)
│   └── http/                       # HTTP interface
│       ├── server.go               # Server initialization
│       ├── serve.go                # HTTP server setup
│       ├── middleware/             # HTTP middleware
│       │   ├── auth.go             # Authentication middleware
│       │   ├── validate.go         # Request validation
│       │   └── limits.go           # Rate limiting
│       ├── routes/                 # HTTP route handlers
│       │   ├── api/                # Public API routes
│       │   └── source/             # Data source routes
│       └── responses/              # Response type definitions
└── infrastructure/                  # Infrastructure Layer (External)
    ├── postgres/                   # PostgreSQL implementation
    │   ├── store/                  # Store implementations
    │   ├── migrations/             # Database migrations
    │   └── sql/                    # SQL queries and schema
    ├── duckdb/                     # DuckDB OLAP implementation
    ├── s3/                         # S3 storage implementation
    ├── aiagent/                    # AI agent integration
    ├── zitadel/                    # Authentication integration
    ├── portkey/                    # AI proxy integration
    └── meterus/                    # Usage analytics integration
```

## Key Components

### Domain Layer (`domain/`)
- **Models**: Core business entities (Project, Dataset, Chat)
- **Commands**: CLI interface using Cobra
- **Configuration**: Environment-based config management
- **Error Handling**: Domain-specific error types

### Application Layer (`application/`)
- **Services**: Business logic implementation
  - `ProjectService`: Project CRUD operations
  - `DatasetService`: Dataset management
  - `ChatService`: Chat functionality
  - `OlapService`: Analytics queries
- **Repositories**: Interface definitions (dependency inversion)

### Interface Layer (`interfaces/http/`)
- **REST API**: Fiber-based HTTP handlers
- **Middleware**: Auth, validation, rate limiting
- **Routes**: Organized by feature (projects, datasets, chats)
- **Swagger**: Auto-generated API documentation

### Infrastructure Layer (`infrastructure/`)
- **PostgreSQL**: Metadata storage with SQLC
- **DuckDB**: OLAP queries and analytics
- **S3**: File storage for datasets
- **External Services**: AI agents, authentication

## Database Architecture

### PostgreSQL (Metadata)
- **Projects**: Project management and organization
- **Datasets**: Dataset metadata and relationships
- **Chats**: Chat history and messages
- **Database Sources**: External database connections
- **Users & Organizations**: Multi-tenant support

### DuckDB (Analytics)
- **OLAP Workloads**: Complex analytical queries
- **Dataset Analysis**: Statistical computations
- **SQL Execution**: User-submitted queries
- **Performance**: Optimized for analytical workloads

### SQLC Integration
- **Type Safety**: Generated Go structs from SQL
- **Query Validation**: Compile-time SQL validation
- **Performance**: Prepared statements
- **Maintainability**: SQL-first approach

## API Design

### REST Endpoints
```
/api/v1/
├── projects/                    # Project management
│   ├── GET /                   # List projects
│   ├── POST /                  # Create project
│   ├── GET /{id}              # Get project details
│   ├── PUT /{id}              # Update project
│   ├── DELETE /{id}           # Delete project
│   └── {id}/datasets/         # Project datasets
├── datasets/                   # Dataset management
├── chats/                     # Chat functionality
├── sql/                       # SQL query execution
└── auth/                      # Authentication
```

### Authentication Flow
1. **Zitadel OAuth**: Frontend initiates OAuth flow
2. **JWT Validation**: Server validates tokens via middleware
3. **Organization Context**: Multi-tenant access control
4. **API Key Support**: Alternative auth for integrations

## Development Patterns

### Service Pattern
```go
// Application service with dependency injection
type ProjectService struct {
    projectRepo repositories.ProjectStoreRepository
}

func NewProjectService(repo repositories.ProjectStoreRepository) *ProjectService {
    return &ProjectService{projectRepo: repo}
}

func (s *ProjectService) Create(params models.CreateProjectParams) (*models.Project, error) {
    return s.projectRepo.Create(context.Background(), params)
}
```

### Repository Pattern
```go
// Interface in application layer
type ProjectStoreRepository interface {
    Create(ctx context.Context, params models.CreateProjectParams) (*models.Project, error)
    Details(ctx context.Context, id, orgID string) (*models.Project, error)
}

// Implementation in infrastructure layer
type postgresProjectStore struct {
    db     *sql.DB
    logger *zap.Logger
}
```

### Error Handling
```go
// Domain-specific errors
var (
    ErrProjectNotFound = errors.New("project not found")
    ErrUnauthorized    = errors.New("unauthorized access")
)

// HTTP error responses
func (h *Handler) handleError(c *fiber.Ctx, err error) error {
    switch err {
    case domain.ErrProjectNotFound:
        return c.Status(404).JSON(fiber.Map{"error": "Project not found"})
    default:
        return c.Status(500).JSON(fiber.Map{"error": "Internal server error"})
    }
}
```

## Configuration

### Environment Variables
```bash
# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=gopie
POSTGRES_USER=gopie
POSTGRES_PASSWORD=password

# OLAP Database
DUCKDB_PATH=/tmp/gopie.duckdb

# S3 Storage
S3_ENDPOINT=http://localhost:9000
S3_ACCESS_KEY=minioadmin
S3_SECRET_KEY=minioadmin
S3_BUCKET=gopie

# Authentication
ZITADEL_URL=http://localhost:4455
ZITADEL_PROJECT_ID=your-project-id

# AI Services
AI_AGENT_URL=http://localhost:8001
PORTKEY_API_KEY=your-portkey-key
```

## Testing Strategy

### Unit Tests
```bash
# Run all tests
go test ./...

# Run with coverage
go test -cover ./...

# Test specific package
go test ./application/services/
```

### Integration Tests
- Database integration with test containers
- S3 integration testing with MinIO
- HTTP endpoint testing with Fiber test utilities

## Performance Considerations

### Database Optimization
- **Connection Pooling**: PostgreSQL connection management
- **Query Optimization**: SQLC for prepared statements
- **Indexing**: Proper database indexes for common queries

### Caching Strategy
- **Application Level**: In-memory caching for frequently accessed data
- **Database Level**: PostgreSQL query result caching
- **CDN**: Static asset caching for uploaded files

### Monitoring
- **Structured Logging**: Zap for performance logging
- **Metrics**: Meterus integration for usage analytics
- **Health Checks**: Endpoint monitoring and alerting

## Security Best Practices

### Authentication & Authorization
- **JWT Validation**: Zitadel token verification
- **Multi-tenant**: Organization-based access control
- **API Keys**: Secure key management for integrations

### Data Protection
- **Input Validation**: Request validation middleware
- **SQL Injection**: SQLC prevents injection attacks
- **File Upload**: Secure file handling and validation

## Common Development Patterns

### Adding New Feature
1. **Define Domain Model** in `domain/models/`
2. **Create Repository Interface** in `application/repositories/`
3. **Implement Service** in `application/services/`
4. **Add Infrastructure** in `infrastructure/`
5. **Create HTTP Handler** in `interfaces/http/routes/`
6. **Update Swagger Docs** with annotations

### Database Changes
1. **Create Migration** in `infrastructure/postgres/migrations/`
2. **Update Schema** in `infrastructure/postgres/sql/schema.sql`
3. **Add Queries** in `infrastructure/postgres/sql/queries/`
4. **Generate SQLC** with `sqlc generate`
5. **Update Models** if needed

### CLI Commands
1. **Add Command** in `domain/cmd/`
2. **Register Command** in `domain/cmd/root.go`
3. **Implement Logic** using existing services
4. **Update Documentation**

## Debugging Tips

1. **Structured Logging**: Use Zap for contextual logging
2. **SQL Debugging**: Enable PostgreSQL query logging
3. **HTTP Debugging**: Use Fiber's built-in middleware
4. **DuckDB Queries**: Log analytical query performance
5. **Configuration**: Verify environment variable loading