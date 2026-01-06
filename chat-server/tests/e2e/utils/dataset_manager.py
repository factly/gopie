import io
import json
import sys
import time
from pathlib import Path
from urllib.parse import urljoin

import boto3
import requests
from botocore.exceptions import ClientError
from vega_datasets import data

from tests.test_config import TestConfig

GOPIE_USER_ID = TestConfig.GOPIE_USER_ID
GOPIE_ORG_ID = TestConfig.GOPIE_ORG_ID

S3_ENDPOINT_URL = TestConfig.S3_ENDPOINT_URL
S3_ACCESS_KEY_ID = TestConfig.S3_ACCESS_KEY_ID
S3_SECRET_ACCESS_KEY = TestConfig.S3_SECRET_ACCESS_KEY
S3_BUCKET_NAME = TestConfig.S3_BUCKET_NAME

LOCAL_DATASET_FOLDER = TestConfig.E2E_DATASET_FOLDER


def validate_config():
    required_vars = [
        "S3_ENDPOINT_URL",
        "S3_ACCESS_KEY_ID",
        "S3_SECRET_ACCESS_KEY",
    ]
    missing_vars = [var for var in required_vars if not globals().get(var)]
    if missing_vars:
        print(f"Missing required environment variables: {', '.join(missing_vars)}")
        sys.exit(1)

    if not Path(LOCAL_DATASET_FOLDER).is_dir():
        print(f"Dataset folder not found at: {LOCAL_DATASET_FOLDER}")
        sys.exit(1)


def create_gopie_project(
    gopie_url: str, name: str | None = None, description: str | None = None
) -> str:
    """
    Create a new project in Gopie.

    Args:
        gopie_url: Base URL for Gopie API
        name: Optional project name. If not provided a default test name is used.
        description: Optional project description.

    Returns:
        The created project ID as a string.
    """
    url = urljoin(gopie_url, "/v1/api/projects")
    headers = _get_gopie_headers()

    payload = {
        "name": name or "Test Dataset Project",
        "description": description or "Dataset project created by automation script for testing.",
    }

    print(f"Creating project '{payload['name']}'...")
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=30)
        response.raise_for_status()

        project_data = response.json().get("data", {})
        project_id = project_data.get("id")

        if not project_id:
            print("Failed to get project ID from API response.")
            sys.exit(1)

        print(f"Successfully created project with ID: {project_id}")
        return project_id
    except requests.exceptions.RequestException as e:
        print(f"Error creating project: {e}")
        print(f"Response body: {getattr(e.response, 'text', 'No response')}")
        sys.exit(1)


def create_s3_bucket_if_not_exists():
    s3_client = boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT_URL,
        aws_access_key_id=S3_ACCESS_KEY_ID,
        aws_secret_access_key=S3_SECRET_ACCESS_KEY,
    )

    try:
        s3_client.head_bucket(Bucket=S3_BUCKET_NAME)
        print(f"Bucket '{S3_BUCKET_NAME}' already exists.")
    except ClientError as e:
        error_code = int(e.response["Error"]["Code"])
        if error_code == 404:
            print(f"Bucket '{S3_BUCKET_NAME}' doesn't exist. Creating it...")
            try:
                s3_client.create_bucket(Bucket=S3_BUCKET_NAME)
                print(f"Successfully created bucket '{S3_BUCKET_NAME}'.")
            except ClientError as create_error:
                print(f"Failed to create bucket '{S3_BUCKET_NAME}': {create_error}")
                sys.exit(1)
        else:
            print(f"Error checking bucket '{S3_BUCKET_NAME}': {e}")
            sys.exit(1)


def upload_file_to_s3(
    file_content: bytes | str,
    file_name: str,
    project_id: str,
    s3_client,
    prefix: str = "dataset",
) -> str:
    """
    Upload file content to S3.

    Args:
        file_content: File content as bytes or string
        file_name: Name for the file (used in S3 key)
        project_id: Project ID for organizing S3 objects
        s3_client: Boto3 S3 client instance
        prefix: Prefix for the S3 object name (e.g., 'dataset', 'vega_dataset')

    Returns:
        S3 path of the uploaded file.

    Raises:
        ClientError: If S3 upload fails.
    """
    current_time = int(time.time())
    object_name = f"{project_id}/{prefix}_{current_time}_{file_name}"

    print(f"Uploading {file_name} to s3://{S3_BUCKET_NAME}/{object_name}...")

    # Convert string to bytes if needed
    if isinstance(file_content, str):
        file_content = file_content.encode("utf-8")

    s3_client.put_object(
        Bucket=S3_BUCKET_NAME,
        Key=object_name,
        Body=file_content,
    )
    s3_path = f"s3://{S3_BUCKET_NAME}/{object_name}"
    print(f"Successfully uploaded {file_name} to {s3_path}")
    return s3_path


def _get_gopie_headers() -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "X-organization-id": GOPIE_ORG_ID,
        "X-user-id": GOPIE_USER_ID,
    }


def ingest_dataset_to_gopie(
    gopie_url: str,
    project_id: str,
    s3_path: str,
    alias: str | None = None,
    description: str | None = None,
) -> str:
    """
    Ingest a dataset from S3 into Gopie project.

    Args:
        gopie_url: Gopie API base URL
        project_id: Target project ID
        s3_path: S3 path to the dataset file
        alias: Optional dataset alias. If not provided, extracted from filename.
        description: Optional dataset description.

    Returns:
        The dataset ID created in Gopie.

    Raises:
        requests.exceptions.RequestException: If API call fails.
    """
    url = urljoin(gopie_url, "/source/s3/upload")
    headers = _get_gopie_headers()

    file_name = s3_path.split("/")[-1]
    dataset_alias = alias or Path(file_name).stem

    payload = {
        "file_path": s3_path,
        "project_id": project_id,
        "created_by": GOPIE_USER_ID,
        "alias": dataset_alias,
        "description": description or f"Dataset for {file_name} ingested via automation script.",
    }

    print(f"Ingesting dataset '{dataset_alias}' from {s3_path}...")
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=300)
        response.raise_for_status()
        dataset_data = response.json().get("data", {}).get("dataset", {})
        dataset_id = dataset_data.get("id")

        if not dataset_id:
            raise ValueError("Dataset ID not found in API response")

        print(f"Successfully ingested dataset '{dataset_alias}' (ID: {dataset_id})")
        return dataset_id
    except requests.exceptions.RequestException as e:
        print(f"Error ingesting dataset '{dataset_alias}': {e}")
        if hasattr(e, "response") and e.response is not None:
            print(f"Response body: {e.response.text}")
        raise


def upload_and_ingest_datasets(
    gopie_url: str,
    project_id: str,
    s3_client,
    local_files: list[Path] | None = None,
    vega_dataset_names: list[str] | None = None,
) -> dict[str, str]:
    """
    Upload datasets to S3 and ingest them into Gopie project.
    Handles both local files and vega datasets uniformly.

    Args:
        gopie_url: Gopie API base URL
        project_id: Target project ID
        s3_client: Boto3 S3 client instance
        local_files: Optional list of local file paths to upload
        vega_dataset_names: Optional list of vega dataset names

    Returns:
        Dictionary mapping dataset_name/filename -> dataset_id in Gopie
    """
    dataset_mapping = {}

    if local_files:
        print(f"Processing {len(local_files)} local file(s)...")
        for file_path in local_files:
            try:
                with open(file_path, "rb") as f:
                    file_content = f.read()

                s3_path = upload_file_to_s3(
                    file_content=file_content,
                    file_name=file_path.name,
                    project_id=project_id,
                    s3_client=s3_client,
                    prefix="dataset",
                )

                dataset_id = ingest_dataset_to_gopie(
                    gopie_url=gopie_url,
                    project_id=project_id,
                    s3_path=s3_path,
                )
                dataset_mapping[file_path.stem] = dataset_id

            except (IOError, ClientError, requests.exceptions.RequestException, ValueError) as e:
                print(f"Error processing local file '{file_path.name}': {e}")
                print("Continuing with remaining files...")
            except Exception as e:
                print(f"Unexpected error processing '{file_path.name}': {e}")
                print("Continuing with remaining files...")

    if vega_dataset_names:
        unique_names = list(dict.fromkeys(vega_dataset_names))
        print(f"Processing {len(unique_names)} vega dataset(s)...")

        for dataset_name in unique_names:
            try:
                dataset_df = getattr(data, dataset_name)()
                print(f"Fetched vega dataset '{dataset_name}' ({len(dataset_df)} rows)")

                csv_buffer = io.StringIO()
                dataset_df.to_csv(csv_buffer, index=False)
                csv_data = csv_buffer.getvalue()

                s3_path = upload_file_to_s3(
                    file_content=csv_data,
                    file_name=f"{dataset_name}.csv",
                    project_id=project_id,
                    s3_client=s3_client,
                    prefix="vega_dataset",
                )

                description = f"Vega dataset '{dataset_name}' for visualization testing"
                dataset_id = ingest_dataset_to_gopie(
                    gopie_url=gopie_url,
                    project_id=project_id,
                    s3_path=s3_path,
                    alias=dataset_name,
                    description=description,
                )
                dataset_mapping[dataset_name] = dataset_id

            except AttributeError:
                print(
                    f"Vega dataset '{dataset_name}' not found in vega_datasets library. Skipping."
                )
            except (ClientError, requests.exceptions.RequestException, ValueError) as e:
                print(f"Error processing vega dataset '{dataset_name}': {e}")
                print("Continuing with remaining datasets...")
            except Exception as e:
                print(f"Unexpected error processing vega dataset '{dataset_name}': {e}")
                print("Continuing with remaining datasets...")

    print(f"Successfully processed {len(dataset_mapping)} dataset(s).")
    return dataset_mapping


def setup_project_and_upload_datasets(
    gopie_url: str, vega_dataset_names: list[str] | None = None
) -> str:
    """
    Main entry point: Create project and upload datasets.

    Args:
        gopie_url: Gopie API base URL
        vega_dataset_names: Optional list of vega dataset names. If not provided,
                           local files from LOCAL_DATASET_FOLDER will be used.

    Returns:
        The created project ID.
    """
    validate_config()

    if vega_dataset_names:
        project_name = "Vega Dataset Test Project"
        project_description = "Project for vega dataset based visualization tests."
    else:
        project_name = None
        project_description = None

    project_id = create_gopie_project(gopie_url, name=project_name, description=project_description)
    create_s3_bucket_if_not_exists()

    s3_client = boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT_URL,
        aws_access_key_id=S3_ACCESS_KEY_ID,
        aws_secret_access_key=S3_SECRET_ACCESS_KEY,
    )

    local_files = None
    if not vega_dataset_names:
        local_files = [f for f in Path(LOCAL_DATASET_FOLDER).iterdir() if f.is_file()]
        if not local_files:
            print("No files found in the dataset folder.")
            return project_id
        print(f"Found {len(local_files)} local file(s) to upload.")

    upload_and_ingest_datasets(
        gopie_url=gopie_url,
        project_id=project_id,
        s3_client=s3_client,
        local_files=local_files,
        vega_dataset_names=vega_dataset_names,
    )

    print("Project setup and dataset upload complete!")
    return project_id


def cleanup_project(gopie_url: str, project_id: str):
    print(f"Starting cleanup for project {project_id}...")

    try:
        s3_client = boto3.client(
            "s3",
            endpoint_url=S3_ENDPOINT_URL,
            aws_access_key_id=S3_ACCESS_KEY_ID,
            aws_secret_access_key=S3_SECRET_ACCESS_KEY,
        )

        response = s3_client.list_objects_v2(Bucket=S3_BUCKET_NAME, Prefix=f"{project_id}/")

        if "Contents" in response:
            objects_to_delete = [{"Key": obj["Key"]} for obj in response["Contents"]]
            s3_client.delete_objects(Bucket=S3_BUCKET_NAME, Delete={"Objects": objects_to_delete})
            print(f"Deleted {len(objects_to_delete)} S3 objects")
        else:
            print("No S3 objects found")

    except ClientError as e:
        print(f"Error cleaning S3 files: {e}")

    # Delete project
    try:
        url = urljoin(gopie_url, f"/v1/api/projects/{project_id}")
        headers = _get_gopie_headers()

        response = requests.delete(url, headers=headers, timeout=30)
        response.raise_for_status()
        print(f"Successfully deleted project {project_id}")

    except requests.exceptions.RequestException as e:
        print(f"Error deleting project: {e}")

    print("Cleanup complete!")
