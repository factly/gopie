# Test Helper Scripts

Utility scripts for test data management and setup.

## Overview

These scripts help with:

- Uploading dataset schemas to the chat server
- Replicating projects from production to local environment
- Uploading CSV files to create test projects

## Prerequisites

```bash
# Install dependencies
cd chat-server
uv sync --dev

# Start required services
docker compose -f docker-compose-noauth.yaml up -d
```

## Scripts

### schema_uploader.py

Upload dataset schemas to the chat server's vector database (Qdrant).

**Use case:** Populate the vector store with schema embeddings for schema search and dataset identification.

```bash
# Upload all schemas for a project
python -m tests.scripts.schema_uploader \
  --project-id your-project-id

# Upload a specific dataset schema
python -m tests.scripts.schema_uploader \
  --project-id your-project-id \
  --dataset-id your-dataset-id

# Use a different base URL
python -m tests.scripts.schema_uploader \
  --project-id your-project-id \
  --base-url http://localhost:8001

# Test connection only
python -m tests.scripts.schema_uploader \
  --project-id test \
  --test-connection
```

**Options:**

| Option              | Description                      | Default                 |
| ------------------- | -------------------------------- | ----------------------- |
| `--project-id`      | Project ID to upload schemas for | Required                |
| `--dataset-id`      | Specific dataset ID (optional)   | All datasets in project |
| `--base-url`        | Chat server base URL             | `http://localhost:8000` |
| `--test-connection` | Only test endpoint connectivity  | False                   |

---

### reset_and_reindex_collection.py

Migrate Qdrant collection to support hybrid search (adds sparse vectors to existing dense vectors).

```bash
# Preview changes first (recommended)
python -m tests.scripts.reset_and_reindex_collection --dry-run

# Run the migration
python -m tests.scripts.reset_and_reindex_collection
```

**⚠️ Warning:** This deletes and recreates your collection. Run `--dry-run` first to preview.

**Options:**

| Option         | Description                    | Default |
| -------------- | ------------------------------ | ------- |
| `--dry-run`    | Preview without making changes | False   |
| `--batch-size` | Points per batch               | 100     |

---

### replicate_prod_to_local.py

Replicate entire projects with datasets from a production Gopie instance to your local instance, or upload CSV files from a local folder.

**Use cases:**

- Test with production data locally
- Create test projects from CSV files
- Migrate data between environments

#### Mode 1: Replicate from Production

```bash
# Replicate a specific project
python -m tests.scripts.replicate_prod_to_local \
  --prod-url http://production-gopie:8000 \
  --local-url http://localhost:8000 \
  --project-id b7711501-e8ee-4804-82dd-5fe5af817dcd

# Replicate multiple projects from a JSON file
python -m tests.scripts.replicate_prod_to_local \
  --prod-url http://production-gopie:8000 \
  --local-url http://localhost:8000 \
  --json-file path/to/projects.json
```

**JSON file format:**

```json
[
  { "project_id": "uuid-1", "other_field": "ignored" },
  { "project_id": "uuid-2", "other_field": "ignored" }
]
```

#### Mode 2: Upload CSV Files

```bash
# Upload all CSV files from a folder
python -m tests.scripts.replicate_prod_to_local \
  --local-url http://localhost:8000 \
  --csv-folder /path/to/csv/files

# With custom project name and description
python -m tests.scripts.replicate_prod_to_local \
  --local-url http://localhost:8000 \
  --csv-folder /path/to/csv/files \
  --project-name "My Test Project" \
  --project-description "Test data for development"
```

**Options:**

| Option                  | Description                        | Required                    |
| ----------------------- | ---------------------------------- | --------------------------- |
| `--local-url`           | Local Gopie API URL                | Always                      |
| `--prod-url`            | Production Gopie API URL           | Replication mode            |
| `--project-id`          | Specific project ID to replicate   | Replication mode (option 1) |
| `--json-file`           | JSON file with project references  | Replication mode (option 2) |
| `--csv-folder`          | Path to folder with CSV files      | CSV upload mode             |
| `--project-name`        | Project name for CSV upload        | Optional                    |
| `--project-description` | Project description for CSV upload | Optional                    |

## Common Workflows

### Setting Up Test Data

1. **Create test project with your own CSV files:**

   ```bash
   # Put CSV files in a folder
   mkdir -p ~/test-data
   cp your-data.csv ~/test-data/

   # Upload to local Gopie
   python -m tests.scripts.replicate_prod_to_local \
     --local-url http://localhost:8000 \
     --csv-folder ~/test-data \
     --project-name "Test Data Project"
   ```

2. **Upload schemas to vector store:**

   ```bash
   # After project is created, upload schemas
   python -m tests.scripts.schema_uploader \
     --project-id <created-project-id>
   ```

3. **Run E2E tests:**
   ```bash
   uv run pytest tests/e2e/ -v
   ```

### Replicating Production Data for Testing

1. **Export project ID from production:**

   ```bash
   # Get project ID from Gopie UI or API
   curl -H "X-Organization-ID: 123" -H "X-User-ID: system" \
     http://production:8000/v1/api/projects
   ```

2. **Replicate to local:**

   ```bash
   python -m tests.scripts.replicate_prod_to_local \
     --prod-url http://production:8000 \
     --local-url http://localhost:8000 \
     --project-id <project-id>
   ```

3. **Upload schemas:**
   ```bash
   python -m tests.scripts.schema_uploader \
     --project-id <local-project-id>
   ```

## Environment Variables

These scripts use settings from `tests/test_config.py`:

| Variable               | Default                 | Description              |
| ---------------------- | ----------------------- | ------------------------ |
| `GOPIE_USER_ID`        | `system`                | User ID for API requests |
| `GOPIE_ORG_ID`         | `123`                   | Organization ID          |
| `S3_ENDPOINT_URL`      | `http://localhost:9000` | MinIO/S3 endpoint        |
| `S3_ACCESS_KEY_ID`     | `minioadmin`            | S3 access key            |
| `S3_SECRET_ACCESS_KEY` | `minioadmin`            | S3 secret key            |
