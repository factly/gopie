import asyncio
import logging

from app.core.config import settings
from app.core.session import SingletonAiohttp
from fastapi import HTTPException

http_session = SingletonAiohttp.get_aiohttp_client()

PREFETCH_API_URL = settings.HUNTING_API_ENDPOINT + "/api/v1/prefetch/"
PROFILE_API_URL = settings.HUNTING_API_ENDPOINT + "/api/v1/profile/description/"
FLOWER_API_ENDPOINT = settings.FLOWER_API_ENDPOINT + "/api/task/result"


async def check_task_status(
    task_id: str, max_retries: int = 10, delay: float = 2.0
) -> bool:
    """
    Check if the prefetch task has completed successfully by polling the result endpoint.
    """
    headers = {"accept": "application/json"}
    FLOWER_API_URL = f"{FLOWER_API_ENDPOINT}/{task_id}"
    logging.info(FLOWER_API_ENDPOINT)

    for _ in range(max_retries):
        try:
            response = await http_session.get(FLOWER_API_URL, headers=headers)
            if response.status != 200:
                logging.warning(f"Failed to get task status: {await response.text()}")
                await asyncio.sleep(delay)
                continue

            data = await response.json()
            state = data.get("state", "").upper()

            logging.info(f"Task {task_id} state: {state}, result: {data.get('result')}")

            if state == "SUCCESS":
                return True
            elif state == "FAILURE":
                return False

            await asyncio.sleep(delay)

        except Exception as e:
            logging.error(f"Error checking task status: {str(e)}")
            await asyncio.sleep(delay)

    return False


async def fetch_dataset_schema(file_path: str):
    """
    Generate a dataset schema by calling the prefetch endpoint and fetch the schema using the profile endpoint.
    """
    try:
        headers = {"accept": "application/json", "Content-Type": "application/json"}

        prefetch_payload = {
            "urls": [file_path],
            "minimal": True,
            "samples_to_fetch": 10,
            "trigger_id": "",
        }

        prefetch_response = await http_session.post(
            PREFETCH_API_URL, json=prefetch_payload, headers=headers
        )

        if prefetch_response.status != 200:
            raise HTTPException(
                prefetch_response.status, await prefetch_response.text()
            )

        prefetch_data = await prefetch_response.json()
        task_id = prefetch_data.get("task_id", "")

        logging.info(f"Prefetch task started with task_id: {task_id}")

        if not task_id:
            raise HTTPException(
                500,
                f"Invalid prefetch response: missing task_id. Response: {prefetch_data}",
            )

        task_success = await check_task_status(task_id)
        if not task_success:
            raise HTTPException(
                500,
                f"Prefetch task failed or timed out. You can track the status at: {FLOWER_API_ENDPOINT}/{task_id}",
            )

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
