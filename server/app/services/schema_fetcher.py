import asyncio
import logging
from http import HTTPStatus

from fastapi import HTTPException

from app.core.config import settings
from app.core.session import SingletonAiohttp

http_session = SingletonAiohttp.get_aiohttp_client()

PREFETCH_API_URL = settings.HUNTING_API_PREFETCH_ENDPOINT
PROFILE_API_URL = settings.HUNTING_API_DESCRIPTION_ENDPOINT
FLOWER_API_ENDPOINT = settings.FLOWER_API_ENDPOINT + "/api/task/result"


async def handle_api_response(response, operation_name):
    if response.status != HTTPStatus.OK:
        error_text = await response.text()
        raise HTTPException(
            status_code=response.status,
            detail=f"{operation_name} API error: {error_text}",
        )
    return await response.json()


async def check_task_status(
    task_id: str, max_retries: int = 10, delay: float = 2.0
) -> bool:
    headers = {"accept": "application/json"}
    flower_api_url = f"{FLOWER_API_ENDPOINT}/{task_id}"

    for _ in range(max_retries):
        try:
            response = await http_session.get(flower_api_url, headers=headers)
            if response.status != HTTPStatus.OK:
                logging.warning(
                    f"Failed to get task status: {await response.text()}"
                )
                await asyncio.sleep(delay)
                continue

            data = await response.json()
            state = data.get("state", "").upper()

            logging.info(
                f"Task {task_id} state: {state}, result: {data.get('result')}"
            )

            if state == "SUCCESS":
                return True
            elif state == "FAILURE":
                return False

            await asyncio.sleep(delay)

        except Exception as e:
            logging.error(f"Error checking task status: {e!s}")
            await asyncio.sleep(delay)

    return False


async def initiate_schema_generation(file_path: str):
    try:
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
        }

        prefetch_payload = {
            "urls": [file_path],
            "minimal": True,
            "samples_to_fetch": 10,
            "trigger_id": "",
        }

        prefetch_response = await http_session.post(
            PREFETCH_API_URL, json=prefetch_payload, headers=headers
        )

        response_data = await handle_api_response(
            prefetch_response, "Prefetch"
        )
        return response_data

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error in initiate_schema_generation: {e!s}")
        raise HTTPException(
            status_code=500,
            detail=f"Error in schema generation initiation: {e!s}",
        ) from e


async def fetch_dataset_schema(
    file_path: str, prefetch_data, check_status: bool = True
):
    try:
        if check_status:
            task_id = prefetch_data.get("task_id", "")
            logging.info(f"Prefetch task started with task_id: {task_id}")

            if not task_id:
                raise HTTPException(
                    status_code=500,
                    detail=f"Invalid prefetch response: missing task_id. "
                    f"Response: {prefetch_data}",
                )

            task_success = await check_task_status(task_id)
            if not task_success:
                raise HTTPException(
                    status_code=500,
                    detail=f"Prefetch task failed or timed out. "
                    f"Track the status at: {FLOWER_API_ENDPOINT}/{task_id}",
                )

        profile_payload = {
            "source": file_path,
            "samples_to_show": 10,
        }

        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
        }

        schema_response = await http_session.get(
            PROFILE_API_URL, params=profile_payload, headers=headers
        )

        response_data = await handle_api_response(schema_response, "Profile")

        return response_data

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Unexpected error in fetch_dataset_schema: {e!s}")
        raise HTTPException(
            status_code=500, detail=f"Error fetching dataset schema: {e!s}"
        ) from e
