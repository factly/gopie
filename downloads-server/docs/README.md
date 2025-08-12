# API Documentation

This directory contains the Swagger/OpenAPI documentation for the Downloads Server API.

## Files

- `swagger.yaml` - OpenAPI specification in YAML format (auto-generated)
- `swagger.json` - OpenAPI specification in JSON format (auto-generated)
- `docs.go` - Generated Go code for embedding Swagger documentation
- `postman-collection.json` - Postman collection for API testing

## Accessing the Documentation

### Live Swagger UI (Built-in) ✨

The server now serves interactive Swagger documentation at:
- **URL**: http://localhost:8000/swagger
- **Direct link**: http://localhost:8000/swagger/index.html

No additional setup required - just start the server and navigate to the URL!

### Regenerating Documentation

If you modify the API annotations in the code, regenerate the documentation:

```bash
# Install swag if not already installed
go install github.com/swaggo/swag/cmd/swag@latest

# Generate documentation
swag init -g main.go --output ./docs --parseDependency --parseInternal
```

### Using Postman Collection

1. Open Postman
2. Import `postman-collection.json`
3. Set environment variables:
   - `base_url`: http://localhost:8000
   - `jwt_token`: Your authentication token
   - `user_id`: Your user ID
   - `org_id`: Your organization ID

### Option 3: Using Redoc

1. Create an HTML file:
```html
<!DOCTYPE html>
<html>
  <head>
    <title>Downloads Server API</title>
    <meta charset="utf-8"/>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://fonts.googleapis.com/css?family=Montserrat:300,400,700|Roboto:300,400,700" rel="stylesheet">
  </head>
  <body>
    <redoc spec-url='./swagger.yaml'></redoc>
    <script src="https://cdn.jsdelivr.net/npm/redoc@latest/bundles/redoc.standalone.js"> </script>
  </body>
</html>
```

2. Serve the HTML file and swagger.yaml using any static file server

## API Endpoints

### Public Endpoints (No Authentication Required)
- `GET /health` - Check service health
- `GET /swagger` - Interactive Swagger UI documentation
- `GET /swagger/*` - Swagger UI assets

### Protected Endpoints (Authentication Required)
- `POST /downloads` - Create a new download job (returns SSE stream)
- `GET /downloads` - List all download jobs (paginated)
- `GET /downloads/{id}` - Get specific download job details
- `DELETE /downloads/{id}` - Delete a download job

## Authentication

Protected endpoints require authentication headers.

Headers required:
- `Authorization: Bearer <token>`
- `x-user-id: <user-id>`
- `x-organization-id: <org-id>`

## Request/Response Examples

### Create Download Job

**Request:**
```json
POST /downloads
Content-Type: application/json

{
  "dataset_id": "dataset_123",
  "sql": "SELECT * FROM sales WHERE year = 2024",
  "format": "csv"
}
```

**Response (SSE Stream):**
```
event: request_received
data: {"message": "Request received, preparing to submit to queue..."}

event: job_created
data: {"id": "550e8400-e29b-41d4-a716-446655440000", "status": "pending", ...}

event: status_update
data: {"type": "status_update", "message": "Processing query..."}

event: complete
data: {"type": "complete", "message": "https://s3.example.com/download-link"}
```

### List Downloads

**Request:**
```
GET /downloads?limit=10&offset=0
```

**Response:**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "sql": "SELECT * FROM sales WHERE year = 2024",
    "dataset_id": "dataset_123",
    "status": "completed",
    "format": "csv",
    "pre_signed_url": "https://s3.example.com/downloads/file.csv?signature=...",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:35:00Z",
    "expires_at": "2024-01-16T10:35:00Z",
    "completed_at": "2024-01-15T10:35:00Z",
    "user_id": "user_456",
    "org_id": "org_789"
  }
]
```

## Status Values

- `pending` - Job is queued for processing
- `processing` - Job is currently being processed
- `completed` - Job completed successfully, download URL available
- `failed` - Job failed, error message available

## Supported Formats

- `csv` - Comma-separated values
- `json` - JSON format
- `parquet` - Apache Parquet format
- `excel` - Microsoft Excel format