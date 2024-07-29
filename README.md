# Project Documentation

## Overview

Gopie is a query engine for csv and parquet files which uses DuckDB under the hood.

## Prerequisites

- Go (version 1.22 or higher)
- Docker and Docker Compose
- Air (for hot reloading)

## Configuration

### Air Configuration

The project uses Air for hot reloading during development. The configuration is stored in the `.air.toml` file at the root of the project. Key settings include:

- Build command: `go build -o ./tmp/main .`
- Binary to run: `./tmp/main serve`
- Directories to exclude: `assets`, `tmp`, `vendor`, `testdata`

### Environment Variables

The project requires a set of environment variables. These are stored in a `config.env` file. To set up:

1. Copy `config.env.example` to `config.env`
2. Modify the values in `config.env` as needed

Key environment variables include:

- `DUCKDB_DSN`: Path to the DuckDB database file
- `LOG_LEVEL`: Logging level (e.g., debug)
- `SERVER_PORT`: Port on which the server runs
- `MASTER_KEY`: Master key for authentication
- `OPEN_AI_API_KEY`: For natural language to text endpoint
- `S3_ACCESS_KEY` and `S3_SECRET_ACCESS_KEY`: Credentials for S3 (Minio) access
- `PORT_KEY_API_KEY` and `PORT_KEY_AI_MODEL`: Settings for PortKey AI integration

## Database

The project uses DuckDB as its database. The database file is stored at the path specified by `DUCKDB_DSN` in the config.

## File Storage

MinIO is used for S3-compatible object storage. It's set up using Docker Compose.

To start MinIO:

```
docker-compose up minio
```

MinIO will be accessible at `http://localhost:9000`.

## Running the Project

1. Ensure all configurations are set up correctly.
2. Start MinIO using Docker Compose.
3. Run the project using Air:

```
air
```

This will start the server with hot reloading enabled.

## Working
Here's a detailed explanation of its workflow:

1. File Upload:
   - Users upload a CSV or Parquet file from their S3 storage using the /source/s3 API endpoint.


2. File Conversion and Storage:

   - Gopie converts the uploaded file into DuckDB format.
   - The converted files are stored in the path specified by the DUCKDB_DSN environment variable (e.g., ./test/main.db).
   - Gopie assigns a unique alphanumeric name to each uploaded file (e.g., gp_hw9NPJ4qX60c).


3. Directory Structure:

   - For each uploaded file, Gopie creates a new folder in the specified path.
   - The folder name matches the assigned alphanumeric name (e.g., gp_hw9NPJ4qX60c).
   - Inside this folder, Gopie creates:
      a) A version.txt file containing the version number of the uploaded file.
      b) A DuckDB file named {version_number}.db (e.g., 178932892971.db), which is the actual converted database.
   - The /source/s3 endpoint returns a table_name to the user, which corresponds to the assigned alphanumeric name.


4. Querying:
   - Users can query the uploaded data using the provided table_name.
   - The directory with table_name specified in query is attached to duckdb main.db if not attached before(this is done because attaching serveral files at the startup, the application is taking a lot of time to start)
   - Queries are sent through Gopie's API, using the table_name to specify which data to query.


## API Endpoints


## Development

- The project is set up for hot reloading using Air.

## Deployment

[Add deployment instructions here]

## Troubleshooting

- If you encounter issues with database connections, ensure the `DUCKDB_DSN` path is correct and the directory exists.
- For S3 storage issues, verify that MinIO is running and the S3 credentials in `config.env` are correct.

## Additional Notes

- The server can be set to read-only mode by setting `SERVER_READ_ONLY=true` in the config.
- Adjust the `DUCKDB_MEMORY_LIMIT` as needed for your system's capabilities.
