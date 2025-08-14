import asyncio
import csv
import uuid
from datetime import datetime
from io import StringIO
from typing import Annotated

import aioboto3
from e2b_code_interpreter import AsyncSandbox
from langchain_core.runnables import RunnableConfig
from langgraph.prebuilt import InjectedState
from langsmith import traceable

from app.core.config import settings
from app.core.session import SingletonAiohttp

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


@traceable(run_type="chain", name="get_python_code_files")
async def get_python_code_files(viz_paths: list[str]):
    python_code_paths = []
    for viz_path in viz_paths:
        viz_path = viz_path.rsplit("-", 1)[0].strip()
        python_code_path = viz_path.replace(".json", ".py")
        if python_code_path not in python_code_paths:
            python_code_paths.append(python_code_path)
    python_code_files = await asyncio.gather(
        *[get_python_code_from_viz(python_code_path) for python_code_path in python_code_paths]
    )
    return python_code_files


@traceable(run_type="chain", name="get_python_code_for_viz")
async def get_python_code_from_viz(viz_path: str):
    viz_path = viz_path.rsplit("-", 1)[0].strip()
    python_code_path = viz_path.replace(".json", ".py")
    client = SingletonAiohttp.get_aiohttp_client()
    async with client.get(python_code_path) as response:
        if response.status == 200:
            return await response.text()
        else:
            return ""


@traceable
def format_dataset_info(datasets: list[Dataset] | None) -> str:
    datasets_csv_info = ""
    if not datasets:
        return ""
    for idx, dataset in enumerate(datasets):
        datasets_csv_info += f"Dataset {idx + 1}: \n\n"
        datasets_csv_info += f"Description: {dataset.description}\n\n"
        datasets_csv_info += f"CSV Path: {dataset.csv_path}\n\n"
    return datasets_csv_info


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
    _ = await sbx.commands.run("pip install altair vl-convert-python")
    return sbx


@traceable(run_type="chain", name="update_sandbox_timeout")
async def update_sandbox_timeout(sandbox: AsyncSandbox):
    await sandbox.set_timeout(settings.E2B_TIMEOUT)


@traceable(run_type="chain", name="upload_csv_files")
async def upload_csv_files(sandbox: AsyncSandbox, datasets: list[Dataset] | None) -> list[str]:
    """
    Asynchronously writes dataset contents as CSV files to the sandbox file system.

    Parameters:
        datasets (list[Dataset]): List of datasets whose data will be converted to CSV and uploaded.

    Returns:
        list[str]: List of file names corresponding to the uploaded CSV files.
    """
    if not datasets:
        return []

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
    Asynchronously reads multiple text files (e.g., JSON) from the sandbox.

    Parameters:
        file_names (list[str]): List of file names to read from the sandbox.

    Returns:
        list[str]: Contents of the files, in the same order as the provided file names.
    """
    tasks = []
    for file_name in file_names:
        tasks.append(sandbox.files.read(file_name))
    return await asyncio.gather(*tasks)


@traceable(run_type="chain", name="get_visualization_result_bytes")
async def get_visualization_result_bytes(
    sandbox: AsyncSandbox, file_names: list[str]
) -> list[bytes]:
    """
    Asynchronously reads multiple binary files (e.g., PNG) from the sandbox.

    Parameters:
        file_names (list[str]): List of file names to read from the sandbox.

    Returns:
        list[bytes]: Raw bytes of the files, in the same order as the provided file names.
    """
    tasks = []
    for file_name in file_names:
        tasks.append(sandbox.files.read(file_name, format="bytes"))
    return await asyncio.gather(*tasks)


@traceable(run_type="chain", name="add_context_to_python_code")
async def add_context_to_python_code(python_code: str, datasets: list[Dataset]) -> str:
    formatted_dataset_info = format_dataset_info(datasets=datasets)
    # Convert dataset info str to comment
    formatted_dataset_info = formatted_dataset_info.replace("\n", "\n# ")
    # Add dataset info as a comment at the top of the python code
    python_code_with_context = f"# Information about the datasets present when this code was run\n{formatted_dataset_info}\n\n{python_code}"
    return python_code_with_context


@traceable(run_type="chain", name="upload_visualization_result_data")
async def upload_visualization_result_data(data: list[str], python_code: str) -> list[str]:
    """
    Asynchronously uploads a list of visualization data strings to S3 storage and returns their public URLs.
    Also uploads the corresponding Python code with the same filename but .py extension.

    Each data item is saved as a uniquely named JSON file under the "visualizations" prefix.
    If python_code is provided, it's saved with the same name but .py extension.
    Raises a ValueError if required AWS credentials or bucket name are missing.

    Parameters:
        data (list[str]): List of string data items to upload.
        python_code (str): Python code to save alongside the JSON configs.

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
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        for idx, item_data in enumerate(data):
            json_file_key = f"visualizations/{timestamp}-{unique_id}-{idx}.json"
            json_task = s3_client.put_object(
                Bucket=bucket_name,
                Key=json_file_key,
                Body=item_data,
            )
            upload_tasks.append(json_task)
            s3_path = f"{s3_host}/{bucket_name}/{json_file_key}"
            s3_paths.append(s3_path)
        py_file_key = f"visualizations/{timestamp}-{unique_id}.py"
        py_task = s3_client.put_object(
            Bucket=bucket_name,
            Key=py_file_key,
            Body=python_code.encode("utf-8"),
        )
        upload_tasks.append(py_task)
        await asyncio.gather(*upload_tasks)
    return s3_paths
