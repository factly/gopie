import asyncio
import logging

from app.core.config import settings
from app.core.session import SingletonAiohttp
from fastapi import HTTPException

http_session = SingletonAiohttp.get_aiohttp_client()

PREFETCH_API_URL = settings.HUNTING_API_ENDPOINT + "/api/v1/prefetch"
PROFILE_API_URL = settings.HUNTING_API_ENDPOINT + "/api/v1/profile/description"
STATUS_API_URL = settings.FLOWER_HUNTING_API_ENDPOINT + "/api/v1/task/status"


async def check_task_status(
    task_id: str, trigger_id: str, max_retries: int = 10
) -> bool:
    """
    Check if the prefetch task has completed successfully.

    Args:
        task_id: The ID of the prefetch task
        trigger_id: The trigger ID of the prefetch task
        max_retries: Maximum number of times to check status

    Returns:
        bool: True if the task completed successfully, False if it failed
    """
    headers = {"accept": "application/json"}
    params = {"task_id": task_id, "trigger_id": trigger_id}

    for _ in range(max_retries):
        try:
            status_response = await http_session.get(
                STATUS_API_URL, params=params, headers=headers
            )

            if status_response.status != 200:
                logging.error(
                    f"Failed to get task status: {await status_response.text()}"
                )
                await asyncio.sleep(2)
                continue

            status_data = await status_response.json()
            if status_data.get("status") == "completed":
                return True
            elif status_data.get("status") == "failed":
                return False

            await asyncio.sleep(2)

        except Exception as e:
            logging.error(f"Error checking task status: {str(e)}")
            await asyncio.sleep(2)

    return False


async def fetch_dataset_schema(file_path: str):
    """
    Generate a dataset schema by calling the prefetch endpoint and fetch the schema using the profile endpoint.
    """
    try:
        headers = {"accept": "application/json", "Content-Type": "application/json"}

        # prefetch_payload = {
        #     "urls": [file_path],
        #     "minimal": True,
        #     "samples_to_fetch": 10,
        #     "trigger_id": "",
        # }

        # prefetch_response = await http_session.post(
        #     PREFETCH_API_URL, json=prefetch_payload, headers=headers
        # )

        # if prefetch_response.status != 200:
        #     raise HTTPException(
        #         prefetch_response.status, await prefetch_response.text()
        #     )

        # prefetch_data = await prefetch_response.json()
        # task_id = prefetch_data.get("task_id", "")
        # trigger_id = prefetch_data.get("trigger_id", "")

        # logging.info(
        #     f"Prefetch task started with task_id: {task_id} and trigger_id: {trigger_id}"
        # )

        # if not task_id or not trigger_id:
        #     raise HTTPException(
        #         500,
        #         f"Invalid prefetch response: missing task_id or trigger_id. Response: {prefetch_data}",
        #     )

        # task_success = await check_task_status(task_id, trigger_id)
        # if not task_success:
        #     raise HTTPException(
        #         500,
        #         f"Prefetch task failed. You can track the status at: {settings.HUNTING_API_ENDPOINT}",
        #     )

        profile_payload = {
            "source": file_path,
            "samples_to_show": 10,
        }

        schema_response = await http_session.get(
            PROFILE_API_URL, params=profile_payload, headers=headers
        )

        if schema_response.status != 200:
            raise HTTPException(schema_response.status, await schema_response.text())

        return await schema_response.json()

    except HTTPException as e:
        raise e
    except Exception as e:
        logging.error(f"Error fetching dataset schema: {str(e)}")
        raise HTTPException(500, f"Error fetching dataset schema: {str(e)}")
