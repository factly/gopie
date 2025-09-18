# AGENTS.md - Go Backend Server

## Build/Lint/Test Commands
```bash
# Development with hot reload
air  # or go run main.go serve

# Build
go build -o gopie main.go

# Tests
go test ./...                    # Run all tests
go test ./path/to/package        # Run single package tests
go test -run TestName ./...      # Run specific test by name
go test -v -cover ./...          # Verbose with coverage

# Formatting & Linting
go fmt ./...                      # Format code
go vet ./...                      # Check for suspicious constructs
swag init                         # Generate Swagger docs
sqlc generate                     # Generate type-safe SQL code
```

## Code Style Guidelines

### Imports
- Group imports: stdlib, external packages, internal packages (separated by blank lines)
- Use absolute imports: `github.com/factly/gopie/...`

### Error Handling
- Use `fmt.Errorf("context: %w", err)` for wrapping errors with context
- Return early on errors, avoid deep nesting
- Log errors with structured logging: `logger.Error("message", zap.Error(err))`

### Naming Conventions
- Files: lowercase with underscores (e.g., `database_source.go`)
- Interfaces: suffix with `Repository` or `Service`
- HTTP handlers: lowercase methods (e.g., `func (h *httpHandler) create(ctx *fiber.Ctx)`)

### Architecture Patterns
- Follow Hexagonal Architecture: domain → application → interfaces → infrastructure
- Use dependency injection via constructors
- Repository pattern for data access
- Service layer for business logic

### Database
- Use SQLC for type-safe queries
- Migrations in `infrastructure/postgres/migrations/`
- Always use context for DB operations