from app.core.config import settings
from app.core.log import logger
from app.core.session import SingletonAiohttp
from app.models.data import DatasetDetails, ProjectDetails
from app.models.schema import ColumnSchema, DatasetSchema, DatasetSummary
from app.services.gopie.sql_executor import SQL_RESPONSE_TYPE


async def get_dataset_info(dataset_id, project_id) -> DatasetDetails:
    http_session = SingletonAiohttp.get_aiohttp_client()

    url = f"{settings.GOPIE_API_ENDPOINT}/v1/api/projects/{project_id}/datasets/{dataset_id}"
    headers = {"accept": "application/json"}

    try:
        async with http_session.get(url, headers=headers) as response:
            data = await response.json()
            return DatasetDetails(**data)
    except Exception as e:
        logger.error(f"Error getting dataset info: {e!s}")
        raise e


async def get_project_info(project_id) -> ProjectDetails:
    http_session = SingletonAiohttp.get_aiohttp_client()

    url = f"{settings.GOPIE_API_ENDPOINT}/v1/api/projects/{project_id}"
    headers = {"accept": "application/json"}

    try:
        async with http_session.get(url, headers=headers) as response:
            data = await response.json()
            return ProjectDetails(**data)
    except Exception as e:
        logger.error(f"Error getting project info: {e!s}")
        raise e


def create_dataset_schema(
    dataset_summary: DatasetSummary,
    sample_data: SQL_RESPONSE_TYPE,
    dataset_details: DatasetDetails,
    project_details: ProjectDetails,
) -> DatasetSchema:
    """
    Create a dataset schema from the given schema data.

    Args:
        schema: The schema data containing the 'summary' field with column info
        sample_data: Sample data for the dataset as a list of dictionaries
        dataset_details: The dataset details
        project_details: The project details

    Returns:
        A DatasetSchema object
    """
    columns: list[ColumnSchema] = []

    for column_data in dataset_summary.summary:
        column_name = column_data.column_name

        samples = []
        if sample_data and isinstance(sample_data, list):
            samples = [item.get(column_name) for item in sample_data if column_name in item]

        column_schema = ColumnSchema(
            **column_data.model_dump(),
            sample_values=samples,
        )

        columns.append(column_schema)

    dataset_schema = DatasetSchema(
        name=dataset_details.alias,
        dataset_name=dataset_details.name,
        dataset_description=dataset_details.description,
        project_custom_prompt=project_details.custom_prompt,
        dataset_custom_prompt=dataset_details.custom_prompt,
        project_id=project_details.id,
        dataset_id=dataset_details.id,
        columns=columns,
    )

    return dataset_schema


def format_schema_for_embedding(
    schema: DatasetSchema,
) -> str:
    """
    Format the schema data into a string for embedding.

    Args:
        schema: The schema data containing the 'summary' field with column info

    Returns:
        A string representation of the schema data
    """
    page_content = f"Dataset Name: {schema.name}\n"
    page_content += f"Dataset Description: {schema.dataset_description}\n"
    for column in schema.columns:
        if not column.column_description:
            raise ValueError(f"Column description not found for column:{column.column_name}")
        page_content += f"Column Name: {column.column_name}\n"
        page_content += f"Column Type: {column.column_type}\n"
        page_content += f"Column Description: {column.column_description}\n"
        page_content += f"Sample Values: {column.sample_values}\n"

    return page_content
