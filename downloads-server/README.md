# downloads-server 📥

**downloads-server** is a helper service for `gopie-server` that handles long-running data downloads. It takes the load off the main app so it stays quick and responsive. It uses a queue and a worker pool to handle back pressure and streams progress updates back to the client with **Server-Sent Events (SSE)**.

---

## When to Use This Server

You should only use this server if you've got `gopie-server` hooked up to **MotherDuck**.

If you're just using a local DuckDB file, `gopie-server` has a basic downloader built-in.

---

## Core Architecture

The service is built around a few key components to keep it scalable and resilient.

---

## Why MotherDuck? 🦆

A local DuckDB file can't be safely read by two different processes at the same time (i.e., `gopie-server` and this one). MotherDuck solves that by being a managed service, which lets us scale reads without everything catching fire.

---

## How It Works

1. **Request & Queueing**  
   A `POST /downloads` request comes in with some SQL. The server logs the job in a Postgres database and shoves it into an in-memory queue.

2. **Worker Pool**  
   A pool of workers is always listening to the queue. When a new job appears, a free worker grabs it. This way, the server can take in requests fast without waiting for downloads to actually finish.

3. **Data Streaming to S3**  
   The worker runs the SQL against MotherDuck and streams the results straight to an S3 bucket as a CSV. It uses an `io.Pipe`, so the server's memory doesn't blow up, even with huge datasets. We're planning to add other formats later.

4. **Real-Time Progress Updates**  
   As it's working, the worker sends out status updates. A subscription manager makes sure these updates get sent to the right client over SSE, so they can see the progress in real-time.

5. **Completion & Pre-signed URL**  
   When the upload is done, the server generates a pre-signed S3 URL that expires after a set time. It updates the job status in Postgres and sends the final URL to the client in a complete event.

---

## API Endpoints

The server exposes a simple RESTful API for managing downloads.

| Method     | Endpoint         | Description                                                                                                                                                                           |
| ---------- | ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **POST**   | `/downloads`     | Creates a new download job. The response is a stream of Server-Sent Events (SSE) that provides real-time updates on the job's status. The connection closes upon completion or error. |
| **GET**    | `/downloads`     | Retrieves a paginated list of all historical download jobs for the user. Supports `limit` and `offset` query parameters.                                                              |
| **GET**    | `/downloads/:id` | Fetches the current status and details of a single download job by its ID.                                                                                                            |
| **DELETE** | `/downloads/:id` | Deletes the record of a download job. This does not delete the file from S3.                                                                                                          |
| **GET**    | `/health`        | A simple health check endpoint. Returns a `200 OK` with the body `"Ok"`.                                                                                                              |

---

## SSE Events for `POST /downloads`

When you create a new download, the server will stream events like these:

```
event: request_received
data: {"message": "Request received, preparing to submit to queue..."}

event: job_created
data: {"id":"...","org_id":"...","user_id":"...","dataset_id":"...","sql":"...","status":"pending", ...}

data: {"download_id":"...","type":"status_update","message":"Processing query..."}

data: {"download_id":"...","type":"status_update","message":"Streaming data to storage..."}

data: {"download_id":"...","type":"status_update","message":"Generating secure download link..."}

data: {"download_id":"...","type":"complete","message":"https://your-s3-url/..."}
```

---

## Configuration

The server is configured using environment variables. You can create a `config.env` file in the root of the project.

```env
# Server Configuration
GOPIE_DS_SERVER_HOST=localhost
GOPIE_DS_SERVER_PORT=8000

# S3 Storage Configuration
GOPIE_DS_S3_ACCESS_KEY=minioadmin
GOPIE_DS_S3_SECRET_KEY=minioadmin
GOPIE_DS_S3_REGION=us-east-1
GOPIE_DS_S3_ENDPOINT=http://localhost:9000
GOPIE_DS_S3_BUCKET=downloads
GOPIE_DS_S3_SSL=false

# Logger Configuration
GOPIE_DS_LOGGER_LEVEL=info
GOPIE_DS_LOGGER_FILE=gopie.log
GOPIE_DS_LOGGER_MODE=dev # 'dev' for pretty console logs, 'prod' for JSON

# MotherDuck Configuration
GOPIE_DS_MOTHERDUCK_DB_NAME=your_db_name
GOPIE_DS_MOTHERDUCK_TOKEN=your_motherduck_token

# Postgres Configuration (for storing job metadata)
GOPIE_DS_POSTGRES_HOST=localhost
GOPIE_DS_POSTGRES_PORT=5432
GOPIE_DS_POSTGRES_DB=gopie_sas
GOPIE_DS_POSTGRES_USER=postgres
GOPIE_DS_POSTGRES_PASSWORD=postgres

# Queue Configuration
GOPIE_DS_QUEUE_WORKERS=10  # Number of concurrent download jobs
GOPIE_DS_QUEUE_SIZE=1000   # Max number of jobs waiting in the queue
```
