import csv
import io
from datetime import datetime

from langchain_core.callbacks import adispatch_custom_event
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from app.core.log import custom_logger as logger
from app.models.message import IntermediateStep
from app.models.query import QueryResult, SingleDatasetQueryResult
from app.services.gopie.sql_executor import execute_sql_with_limit
from app.services.qdrant.get_schema import get_schema_from_qdrant
from app.utils.langsmith.prompt_manager import get_prompt_llm_chain
from app.workflow.events.event_utils import configure_node
from app.workflow.graph.single_dataset_graph.types import (
    SingleDatasetInfo,
    State,
)
from app.workflow.graph.sql_planner_graph.types import ColumnAssumptions


class ExtractColumnAssumptionsOutput(BaseModel):
    column_assumptions: list[ColumnAssumptions] = Field(
        description="Column assumptions for the dataset with fuzzy values for matching",
        default=[],
    )


def convert_rows_to_csv(rows: list[dict]) -> str:
    """
    Convert a list of dictionaries into a CSV-formatted string with special handling for certain cell values.

    Each row in the output CSV includes a "row_num" column as the first field.
    Cell values are converted as follows: `None` becomes "NULL",
    empty strings become "EMPTY_STRING",
    strings containing only whitespace become "WHITESPACE_ONLY",
    and numeric zeros become "0".
    Returns an empty string if the input list is empty.

    Parameters:
        rows (list[dict]): List of dictionaries representing table rows.

    Returns:
        str: CSV-formatted string representing the input rows.
    """
    if not rows:
        return ""

    output = io.StringIO()
    writer = csv.writer(output)

    if rows:
        headers = ["row_num"] + list(rows[0].keys())
        writer.writerow(headers)

        for idx, row in enumerate(rows, 1):
            record = [str(idx)]

            for value in row.values():
                if value is None:
                    record.append("NULL")
                elif value == "":
                    record.append("EMPTY_STRING")
                elif isinstance(value, str) and value.strip() == "":
                    record.append("WHITESPACE_ONLY")
                elif isinstance(value, (int, float)) and value == 0:
                    record.append("0")
                else:
                    record.append(str(value))

            writer.writerow(record)

    return output.getvalue()


@configure_node(
    role="intermediate",
    progress_message="Preparing data...",
)
async def prepare_data(state: State, config: RunnableConfig):
    user_query = state.get("user_query", "") or ""
    dataset_id = state.get("dataset_id", None)

    org_id = config.get("metadata", {}).get("org_id") or ""
    user_id = config.get("metadata", {}).get("user") or ""

    query_result = QueryResult(
        original_user_query=user_query,
        execution_time=0,
        timestamp=datetime.now(),
    )

    query_result.single_dataset_query_result = SingleDatasetQueryResult(
        user_friendly_dataset_name=None,
        dataset_name=None,
        sql_queries=None,
        non_sql_response=None,
        error=None,
        retry_count=0,
    )

    try:
        if not dataset_id:
            raise Exception("No dataset ID provided")

        dataset_schema = await get_schema_from_qdrant(dataset_id=dataset_id)
        if dataset_schema is None:
            raise Exception("Schema fetch error: Dataset not found")

        dataset_name = dataset_schema.dataset_name
        user_provided_dataset_name = dataset_schema.name

        query_result.single_dataset_query_result.user_friendly_dataset_name = (
            user_provided_dataset_name
        )
        query_result.single_dataset_query_result.dataset_name = dataset_name

        sample_data_query = f"SELECT * FROM {dataset_name} LIMIT 50"
        sample_data = await execute_sql_with_limit(
            query=sample_data_query, org_id=org_id, user_id=user_id
        )

        rows_csv = convert_rows_to_csv(sample_data)  # type: ignore

        column_assumptions = []
        try:
            chain = get_prompt_llm_chain(
                "extract_column_assumptions",
                config,
                schema=ExtractColumnAssumptionsOutput,
            )

            response = await chain.ainvoke(
                {
                    "user_query": user_query,
                    "dataset_schema": dataset_schema,
                }
            )
            column_assumptions = response.column_assumptions or []

            logger.debug(f"Extracted column assumptions: {column_assumptions}")
        except Exception as e:
            logger.warning(f"Failed to extract column assumptions: {e!s}")
            column_assumptions = []

        dataset_info = SingleDatasetInfo(
            dataset_schema=dataset_schema,
            sample_data_csv=rows_csv,
            column_assumptions=column_assumptions if column_assumptions else None,
            correct_column_requirements=None,
        )

        return {
            "user_query": user_query,
            "query_result": query_result,
            "dataset_info": dataset_info,
        }
    except Exception as e:
        err_msg = f"Error in preparing data: {str(e)}"
        query_result.single_dataset_query_result.error = err_msg

        logger.exception(err_msg)

        await adispatch_custom_event(
            "gopie-agent",
            {
                "content": "Error preparing data.",
            },
        )

        return {
            "messages": [IntermediateStep(content=str(err_msg))],
            "query_result": query_result,
        }
