from typing import Optional

from app.core.config import settings
from app.core.log import custom_logger as logger
from app.models.data import DatasetDetails, ProjectDetails
from app.models.schema import ColumnSchema, DatasetSchema, DatasetSummary
from app.services.gopie.client import GopieClient
from app.services.gopie.sql_executor import SQL_RESPONSE_TYPE


async def get_dataset_info(
    dataset_id: str,
    project_id: str,
    org_id: Optional[str] = None,
    is_view: bool = False,
) -> DatasetDetails:
    """Get dataset information from Gopie API.

    Args:
        dataset_id: The dataset ID (or view ID if is_view is True)
        project_id: The project ID
        org_id: Optional organization ID for multi-tenant support
        is_view: Whether the dataset_id refers to a view

    Returns:
        DatasetDetails object
    """
    client = GopieClient(org_id=org_id)
    if is_view:
        path = f"/v1/api/projects/{project_id}/views/{dataset_id}"
    else:
        path = f"/v1/api/projects/{project_id}/datasets/{dataset_id}"

    try:
        async with await client.get(path) as response:
            response_data = await response.json()
        data = response_data["data"] if is_view else response_data
        if is_view and data.get("sql_query"):
            data["description"] = f"{data['description']}\n\nSQL Query:\n{data['sql_query']}"
        return DatasetDetails(**data)
    except Exception as e:
        logger.exception(f"Error getting dataset info: {e!s}")
        raise e


async def get_project_info(
    project_id: str,
    org_id: Optional[str] = None,
) -> ProjectDetails:
    """Get project information from Gopie API.

    Args:
        project_id: The project ID
        org_id: Optional organization ID for multi-tenant support

    Returns:
        ProjectDetails object
    """
    client = GopieClient(org_id=org_id)
    path = f"/v1/api/projects/{project_id}"

    try:
        async with await client.get(path) as response:
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
    org_id: str,
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
        org_id=org_id,
        columns=columns,
    )

    return dataset_schema


def _estimate_tokens(text: str) -> int:
    """Estimate token count using 1 token ≈ 4 chars approximation."""
    return len(text) // 4


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
