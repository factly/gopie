from app.core.config import settings
from app.core.log import custom_logger as logger
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
        logger.exception(f"Error getting dataset info: {e!s}")
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
        logger.exception(f"Error getting project info: {e!s}")
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


def _estimate_tokens(text: str) -> int:
    """Estimate token count using 1 token ≈ 1.5 words approximation."""
    word_count = len(text.split())
    return int(word_count / 1.5)


def _build_page_content(
    schema: DatasetSchema,
    include_sample_values: bool = True,
    include_column_type: bool = True,
    include_description: bool = True,
) -> str:
    """Build page content with optional fields."""
    page_content = f"Dataset Name: {schema.name}\n"
    page_content += f"Dataset Description: {schema.dataset_description}\n"
    for column in schema.columns:
        page_content += f"Column Name: {column.column_name}\n"
        if include_column_type:
            page_content += f"Column Type: {column.column_type}\n"
        if include_description:
            page_content += f"Column Description: {column.description}\n"
        if include_sample_values:
            page_content += f"Sample Values: {column.sample_values}\n"

    return page_content


def format_schema_for_embedding(
    schema: DatasetSchema,
) -> str:
    """
    Format the schema data into a string for embedding.

    Args:
        schema: The schema data containing the 'summary' field with column info

    Returns:
        A string representation of the schema data, truncated if necessary
    """
    max_tokens = settings.EMBEDDINGS_MAX_TOKEN

    # Try with all fields
    page_content = _build_page_content(schema)
    if max_tokens is None:
        return page_content
    if _estimate_tokens(page_content) <= max_tokens:
        return page_content

    # Drop sample values
    page_content = _build_page_content(schema, include_sample_values=False)
    logger.info(
        f"Sample values dropped for {schema.name}. Token count: {_estimate_tokens(page_content)}"
    )
    if _estimate_tokens(page_content) <= max_tokens:
        return page_content

    # Drop sample values and column type
    page_content = _build_page_content(
        schema, include_sample_values=False, include_column_type=False
    )
    logger.info(
        f"Sample values and column type dropped for {schema.name}. Token count: {_estimate_tokens(page_content)}"
    )
    if _estimate_tokens(page_content) <= max_tokens:
        return page_content

    # Drop sample values, column type, and description
    page_content = _build_page_content(
        schema,
        include_sample_values=False,
        include_column_type=False,
        include_description=False,
    )
    logger.info(
        f"Sample values, column type, and description dropped for {schema.name}. Token count: {_estimate_tokens(page_content)}"
    )
    return page_content
