from app.core.config import settings
from app.core.session import SingletonAiohttp
from app.models.data import Dataset_details


async def get_dataset_info(dataset_id, project_id) -> Dataset_details:
    http_session = SingletonAiohttp.get_aiohttp_client()

    url = f"{settings.GOPIE_API_ENDPOINT}/v1/api/projects/{project_id}/datasets/{dataset_id}"
    headers = {"accept": "application/json"}

    async with http_session.get(url, headers=headers) as response:
        data = await response.json()
        return Dataset_details(**data)
