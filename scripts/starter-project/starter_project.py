import os
import sys
import json
import logging
import time
from pathlib import Path
from urllib.parse import urljoin

import requests
import boto3
from botocore.exceptions import ClientError

# --- Configuration ---
# Configure logging for clear output
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# --- Read Configuration from Environment Variables ---
# Best practice to avoid hardcoding credentials and endpoints
GOPIE_API_BASE_URL = os.getenv("GOPIE_API_BASE_URL")
# The user ID and organization ID are required for API requests
GOPIE_USER_ID = "system"
GOPIE_ORG_ID = "system"

S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL")
S3_ACCESS_KEY_ID = os.getenv("S3_ACCESS_KEY_ID")
S3_SECRET_ACCESS_KEY = os.getenv("S3_SECRET_ACCESS_KEY")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "gopie")

# Local folder containing the datasets to upload
LOCAL_DATASET_FOLDER = os.getenv("LOCAL_DATASET_FOLDER", "./datasets/")


def validate_config():
    """Ensure all required environment variables are set."""
    required_vars = [
        "GOPIE_API_BASE_URL",
        "S3_ENDPOINT_URL",
        "S3_ACCESS_KEY_ID",
        "S3_SECRET_ACCESS_KEY",
    ]
    missing_vars = [var for var in required_vars if not globals().get(var)]
    if missing_vars:
        logging.error(
            f"Missing required environment variables: {', '.join(missing_vars)}"
        )
        sys.exit(1)

    if not Path(LOCAL_DATASET_FOLDER).is_dir():
        logging.error(f"Dataset folder not found at: {LOCAL_DATASET_FOLDER}")
        sys.exit(1)


def create_gopie_project() -> str:
    """
    Creates a new project in gopie via the API.

    Returns:
        The ID of the newly created project.
    """
    url = urljoin(GOPIE_API_BASE_URL, "/v1/api/projects")
    headers = {
        "Content-Type": "application/json",
        # The Go code derives these from middleware, typically from headers or a token.
        # We'll pass them directly.
        "X-User-ID": GOPIE_USER_ID,
        "X-Organization-ID": GOPIE_ORG_ID,
    }
    payload = {
        "name": "Starter Project",
        "description": "This is a starter project created by the Python automation script.",
    }

    logging.info(f"Creating project '{payload['name']}'...")
    try:
        response = requests.post(
            url, headers=headers, data=json.dumps(payload), timeout=30
        )
        response.raise_for_status()  # Raises an exception for 4xx/5xx responses

        project_data = response.json().get("data", {})
        logging.info(f"data from project {project_data}")
        project_id = project_data.get("id")

        if not project_id:
            logging.error("Failed to get project ID from API response.")
            sys.exit(1)

        logging.info(f"Successfully created project with ID: {project_id}")
        return project_id
    except requests.exceptions.RequestException as e:
        logging.error(f"Error creating project: {e}")
        logging.error(
            f"Response body: {e.response.text if e.response else 'No response'}"
        )
        sys.exit(1)


def upload_files_to_s3(project_id: str) -> list[str]:
    """
    Uploads all files from the local dataset folder to S3/MinIO.

    Returns:
        A list of the S3 paths for the uploaded files.
    """
    s3_client = boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT_URL,
        aws_access_key_id=S3_ACCESS_KEY_ID,
        aws_secret_access_key=S3_SECRET_ACCESS_KEY,
    )

    local_files = [f for f in Path(LOCAL_DATASET_FOLDER).iterdir() if f.is_file()]
    uploaded_s3_paths = []

    if not local_files:
        logging.warning("No files found in the dataset folder to upload.")
        return []

    logging.info(
        f"Found {len(local_files)} files to upload to S3 bucket '{S3_BUCKET_NAME}'."
    )

    for file_path in local_files:
        # Create object name with pattern: {project_id}/dataset_{time_in_seconds}_{file_name}
        current_time = int(time.time())
        object_name = f"{project_id}/dataset_{current_time}_{file_path.name}"
        logging.info(
            f"Uploading {file_path.name} to s3://{S3_BUCKET_NAME}/{object_name}..."
        )
        try:
            s3_client.upload_file(str(file_path), S3_BUCKET_NAME, object_name)
            s3_path = f"s3://{S3_BUCKET_NAME}/{object_name}"
            uploaded_s3_paths.append(s3_path)
            logging.info(f"Successfully uploaded {file_path.name}.")
        except ClientError as e:
            logging.error(f"Failed to upload {file_path.name}: {e}")
            # Decide if you want to stop on failure or continue
            sys.exit(1)

    return uploaded_s3_paths


def create_dataset_from_s3(project_id: str, s3_path: str):
    """
    Triggers the gopie API to ingest an S3 file as a new dataset.
    """
    url = urljoin(GOPIE_API_BASE_URL, "/source/s3/upload")
    headers = {
        "Content-Type": "application/json",
        "X-Organization-ID": GOPIE_ORG_ID,
        "X-User-ID": GOPIE_USER_ID,
    }

    # Generate an alias from the filename (e.g., "sales.csv" -> "sales")
    file_name = s3_path.split("/")[-1]
    alias = Path(file_name).stem

    print("s3_path", s3_path)
    payload = {
        "file_path": s3_path,
        "project_id": project_id,
        "created_by": GOPIE_USER_ID,
        "alias": alias,
        "description": f"Dataset for {file_name} ingested via automation script.",
    }

    logging.info(f"Ingesting dataset '{alias}' from {s3_path}...")
    try:
        response = requests.post(
            url, headers=headers, data=json.dumps(payload), timeout=300
        )  # Longer timeout for ingestion
        response.raise_for_status()
        dataset_data = response.json().get("data", {}).get("dataset", {})
        logging.info(f"Successfully ingested dataset. ID: {dataset_data.get('ID')}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Error ingesting dataset {alias}: {e}")
        logging.error(
            f"Response body: {e.response.text if e.response else 'No response'}"
        )
        # Continue to the next file instead of exiting


def main():
    """Main execution function."""
    validate_config()

    # Step 1: Create the project
    project_id = create_gopie_project()

    # Step 2: Upload local files to S3
    s3_paths = upload_files_to_s3(project_id)

    if not s3_paths:
        logging.info("No files were uploaded to S3. Exiting.")
        return

    # Step 3: Ingest each S3 file as a dataset in the project
    logging.info(
        f"Starting dataset ingestion for {len(s3_paths)} files into project {project_id}."
    )
    for path in s3_paths:
        create_dataset_from_s3(project_id=project_id, s3_path=path)

    logging.info("Starter project setup complete!")


if __name__ == "__main__":
    main()
