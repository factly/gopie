import asyncio
import csv
import json
import uuid
from datetime import datetime
from io import StringIO
from typing import Annotated
from urllib.parse import urlparse

import aioboto3
from e2b_code_interpreter import AsyncSandbox
from langchain_core.runnables import RunnableConfig
from langgraph.prebuilt import InjectedState
from langsmith import traceable

from app.core.config import settings
from app.core.log import logger

from .types import Dataset


def list_to_csv(list_dict: list[list]) -> str:
    output = StringIO()
    writer = csv.writer(output)
    writer.writerows(list_dict)
    return output.getvalue()


def datasets_to_csv(datasets: list[Dataset]):
    results = []
    for dataset_index, dataset in enumerate(datasets):
        if dataset.data:
            csv_data = list_to_csv(dataset.data)
            file_name = f"result_{dataset_index}.csv"
            dataset.csv_path = file_name
            results.append((file_name, csv_data))
    return results


@traceable(run_type="chain", name="get_sandbox")
async def get_sandbox():
    """
    Asynchronously creates and returns a sandboxed Python environment preconfigured for data visualization.

    Raises:
        ValueError: If the E2B API key is not set in the configuration.

    Returns:
        AsyncSandbox: An instance with the specified timeout and the 'altair' package installed.
    """
    if not settings.E2B_API_KEY:
        raise ValueError("E2B API key is not set. Please set up E2B to enable visualizations.")
    sbx = await AsyncSandbox.create(timeout=settings.E2B_TIMEOUT, api_key=settings.E2B_API_KEY)
    _ = await sbx.commands.run("pip install altair")
    return sbx


@traceable(run_type="chain", name="update_sandbox_timeout")
async def update_sandbox_timeout(sandbox: AsyncSandbox):
    await sandbox.set_timeout(settings.E2B_TIMEOUT)


@traceable(run_type="chain", name="upload_csv_files")
async def upload_csv_files(sandbox: AsyncSandbox, datasets: list[Dataset]) -> list[str]:
    """
    Asynchronously writes dataset contents as CSV files to the sandbox file system.

    Parameters:
    	datasets (list[Dataset]): List of datasets whose data will be converted to CSV and uploaded.

    Returns:
    	list[str]: List of file names corresponding to the uploaded CSV files.
    """
    csv_files = datasets_to_csv(datasets)
    tasks = []
    for file_name, csv_data in csv_files:
        tasks.append(sandbox.files.write(file_name, csv_data))
    await asyncio.gather(*tasks)
    return [file_name for file_name, _ in csv_files]


@traceable(run_type="chain", name="run_python_code")
async def run_python_code(
    code: str,
    sandbox: Annotated[AsyncSandbox, InjectedState("sandbox")],
    config: RunnableConfig,
):
    """Run python code in a jupyter notebook sandbox.
    Already has basic data visualization libraries installed.
    Always use altair to create visualizations and save them to json.
    """
    execution = await sandbox.run_code(code)
    return execution.logs


@traceable(run_type="chain", name="get_visualization_result_data")
async def get_visualization_result_data(sandbox: AsyncSandbox, file_names: list[str]) -> list[str]:
    """
    Asynchronously reads the contents of multiple files from the sandbox environment.

    Parameters:
        file_names (list[str]): List of file names to read from the sandbox.

    Returns:
        list[str]: Contents of the files, in the same order as the provided file names.
    """
    tasks = []
    for file_name in file_names:
        tasks.append(sandbox.files.read(file_name))
    return await asyncio.gather(*tasks)


@traceable(run_type="chain", name="upload_visualization_result_data")
async def upload_visualization_result_data(data: list[str], python_code: str | None = None) -> list[str]:
    """
    Asynchronously uploads a list of visualization data strings to S3 storage and returns their public URLs.
    Also uploads the corresponding Python code with the same filename but .py extension.

    Each data item is saved as a uniquely named JSON file under the "visualizations" prefix.
    If python_code is provided, it's saved with the same name but .py extension.
    Raises a ValueError if required AWS credentials or bucket name are missing.

    Parameters:
        data (list[str]): List of string data items to upload.
        python_code (str | None): Python code to save alongside the JSON configs.

    Returns:
        list[str]: URLs of the uploaded files in S3 storage.
    """

    access_key_id = settings.S3_ACCESS_KEY
    secret_access_key = settings.S3_SECRET_KEY
    region = settings.S3_REGION
    bucket_name = settings.S3_BUCKET
    s3_host = settings.S3_HOST

    if not all([access_key_id, secret_access_key, bucket_name]):
        raise ValueError("AWS credentials or bucket name not set in environment variables")

    session = aioboto3.Session()
    s3_paths = []
    async with session.client(  # type: ignore
        "s3",
        endpoint_url=s3_host,
        region_name=region,
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
    ) as s3_client:

        upload_tasks = []
        for item_data in data:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            unique_id = str(uuid.uuid4())[:8]
            json_file_key = f"visualizations/{timestamp}-{unique_id}.json"
            json_task = s3_client.put_object(
                Bucket=bucket_name,
                Key=json_file_key,
                Body=item_data.encode("utf-8"),
            )
            upload_tasks.append(json_task)

            if python_code:
                py_file_key = f"visualizations/{timestamp}-{unique_id}.py"
                py_task = s3_client.put_object(
                    Bucket=bucket_name,
                    Key=py_file_key,
                    Body=python_code.encode("utf-8"),
                )
                upload_tasks.append(py_task)

            # s3_path = f"s3://{bucket_name}/{file_key}"
            s3_path = f"{s3_host}/{bucket_name}/{json_file_key}"
            s3_paths.append(s3_path)
        await asyncio.gather(*upload_tasks)
    return s3_paths



@traceable(run_type="chain", name="get_python_code_from_paths")
async def get_python_code_from_paths(json_s3_paths: list[str]) -> list[str]:
    """
    Downloads Python code files corresponding to JSON config files from S3 storage.

    Parameters:
        json_s3_paths (list[str]): List of S3 URLs for JSON config files.

    Returns:
        list[str]: List of Python code strings. Empty string if code not found for a path.
    """
    if not json_s3_paths:
        return []

    access_key_id = settings.S3_ACCESS_KEY
    secret_access_key = settings.S3_SECRET_KEY
    region = settings.S3_REGION
    bucket_name = settings.S3_BUCKET
    s3_host = settings.S3_HOST

    if not all([access_key_id, secret_access_key, bucket_name]):
        raise ValueError("AWS credentials or bucket name not set in environment variables")

    session = aioboto3.Session()
    python_codes = []

    async with session.client(  # type: ignore
        "s3",
        endpoint_url=s3_host,
        region_name=region,
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
    ) as s3_client:

        for json_path in json_s3_paths:
            try:
                parsed_url = urlparse(json_path)
                if parsed_url.netloc == f"{bucket_name}":
                    json_key = parsed_url.path.lstrip('/')
                else:
                    path_parts = parsed_url.path.lstrip('/').split('/', 1)
                    if len(path_parts) > 1:
                        json_key = path_parts[1]
                    else:
                        json_key = path_parts[0]

                py_key = json_key.replace('.json', '.py')

                response = await s3_client.get_object(Bucket=bucket_name, Key=py_key)
                content = await response['Body'].read()
                python_codes.append(content.decode('utf-8'))

            except Exception as e:
                logger.warning(f"Failed to download Python code for {json_path}: {str(e)}")
                python_codes.append("")

    return python_codes