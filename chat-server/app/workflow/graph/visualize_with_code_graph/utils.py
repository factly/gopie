import asyncio
import csv
import uuid
from datetime import datetime
from io import StringIO
from typing import Annotated, List

import aioboto3
from e2b_code_interpreter import AsyncSandbox
from langchain_core.runnables import RunnableConfig
from langgraph.prebuilt import InjectedState
from langsmith import traceable

from app.core.config import settings

from .types import Dataset


def list_to_csv(list_dict: list[list]) -> str:
    output = StringIO()
    writer = csv.writer(output)
    writer.writerows(list_dict)
    return output.getvalue()


def datasets_to_csv(datasets: List[Dataset]):
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
    sbx = await AsyncSandbox.create(
        timeout=settings.E2B_TIMEOUT, api_key=settings.E2B_API_KEY
    )
    _ = await sbx.commands.run("pip install altair")
    return sbx


@traceable(run_type="chain", name="update_sandbox_timeout")
async def update_sandbox_timeout(sandbox: AsyncSandbox):
    await sandbox.set_timeout(settings.E2B_TIMEOUT)


@traceable(run_type="chain", name="upload_csv_files")
async def upload_csv_files(
    sandbox: AsyncSandbox, datasets: List[Dataset]
) -> List[str]:
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
    Always use altair to create visualizations.
    Save the visualizations to json.
    """
    execution = await sandbox.run_code(code)
    return execution.logs


@traceable(run_type="chain", name="get_visualization_result_data")
async def get_visualization_result_data(
    sandbox: AsyncSandbox, file_names: List[str]
) -> List[str]:
    tasks = []
    for file_name in file_names:
        tasks.append(sandbox.files.read(file_name))
    return await asyncio.gather(*tasks)


@traceable(run_type="chain", name="upload_visualization_result_data")
async def upload_visualization_result_data(data: List[str]) -> List[str]:
    """Upload visualization data to S3 and return the S3 paths.

    Args:
        data: A list of string data to upload to S3

    Returns:
        A list of S3 paths where the data was uploaded
    """

    access_key_id = settings.S3_ACCESS_KEY
    secret_access_key = settings.S3_SECRET_KEY
    region = settings.S3_REGION
    bucket_name = settings.S3_BUCKET
    s3_host = settings.S3_HOST

    if not all([access_key_id, secret_access_key, bucket_name]):
        raise ValueError(
            "AWS credentials or bucket name not set in environment variables"
        )

    session = aioboto3.Session()
    s3_paths = []
    async with session.client(
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
            file_key = f"visualizations/{timestamp}-{unique_id}.json"
            task = s3_client.put_object(
                Bucket=bucket_name,
                Key=file_key,
                Body=item_data.encode("utf-8"),
            )
            upload_tasks.append(task)
            s3_path = f"s3://{bucket_name}/{file_key}"
            s3_paths.append(s3_path)
        await asyncio.gather(*upload_tasks)
    return s3_paths
