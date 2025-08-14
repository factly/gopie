import csv
import io
import json
from datetime import datetime

from langchain_core.callbacks.manager import adispatch_custom_event
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from app.core.constants import SQL_QUERIES_GENERATED, SQL_QUERIES_GENERATED_ARG
from app.models.query import (
    QueryResult,
    SingleDatasetQueryResult,
    SqlQueryInfo,
)
from app.services.gopie.sql_executor import (
    execute_sql,
    execute_sql_with_limit,
    truncate_if_too_large,
)
from app.services.qdrant.get_schema import get_schema_from_qdrant
from app.utils.langsmith.prompt_manager import get_prompt
from app.utils.model_registry.model_provider import get_configured_llm_for_node
from app.workflow.events.event_utils import (
    configure_node,
    stream_dynamic_message,
)
from app.workflow.graph.single_dataset_graph.types import State


class ProcessQueryOutput(BaseModel):
    sql_queries: list[str] = Field(description="SQL queries without semicolon", default=[])
    explanations: list[str] = Field(
        description="""Concise explanation for each query including: Query strategy (what data is being
        retrieved and how), table metadata (table name and content type), key columns and their data types, any aggregations/calculations, and expected output format...""",
        default=[],
    )
    response_for_non_sql: str = Field(
        description="Brief explanation for non-sql response", default=""
    )
    user_friendly_response: str = Field(
        description="A short user friendly (no technical jargon or error messages revealed in this field) "
        "message not more than 200 characters telling why there was no SQL query generated otherwise this field should be empty",
        default="",
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
    progress_message="Processing query...",
)
async def process_query(state: State, config: RunnableConfig) -> dict:
    """
    Processes a user query against a specified dataset, generating and executing SQL queries or providing non-SQL responses using a language model.

    This asynchronous function orchestrates the workflow for handling a user query:
    it retrieves dataset schema and sample data, constructs prompts for a language model,
    parses the model's response for SQL queries and explanations,
    executes the queries if present, and compiles the results into a structured response.
    If no SQL queries are generated, it returns the non-SQL response from the model.
    Errors encountered during processing are captured and included in the result.

    Returns:
        dict: A dictionary containing a list of AIMessage objects with the serialized query result and the structured query result object.
    """
    user_query = state.get("user_query", "") or ""
    dataset_id = state.get("dataset_id", None)
    prev_query_result = state.get("query_result", None)
    previous_sql_queries = state.get("previous_sql_queries", [])
    validation_result = state.get("validation_result", None)

    query_result = QueryResult(
        original_user_query=user_query,
        execution_time=0,
        timestamp=datetime.now(),
    )

    query_result.single_dataset_query_result = SingleDatasetQueryResult(
        user_friendly_dataset_name=None,
        dataset_name=None,
        sql_results=None,
        response_for_non_sql=None,
        error=None,
    )

    try:
        if not dataset_id:
            raise Exception("No dataset ID provided")

        dataset_schema = await get_schema_from_qdrant(dataset_id=dataset_id)
        if dataset_schema is None:
            raise Exception("Schema fetch error: Dataset not found")

        dataset_name = dataset_schema.dataset_name
        user_provided_dataset_name = dataset_schema.name

        sample_data_query = f"SELECT * FROM {dataset_name} LIMIT 50"
        sample_data = await execute_sql_with_limit(query=sample_data_query)

        rows_csv = convert_rows_to_csv(sample_data)  # type: ignore

        prompt_messages = get_prompt(
            "process_query",
            user_query=user_query,
            dataset_name=dataset_name,
            dataset_schema=dataset_schema,
            rows_csv=rows_csv,
            prev_query_result=prev_query_result,
            previous_sql_queries=previous_sql_queries,
            validation_result=validation_result,
        )

        llm = get_configured_llm_for_node("process_query", config, schema=ProcessQueryOutput)

        response = await llm.ainvoke(prompt_messages)

        sql_queries = response.sql_queries
        explanations = response.explanations
        response_for_non_sql = response.response_for_non_sql

        query_result.single_dataset_query_result.user_friendly_dataset_name = (
            user_provided_dataset_name
        )
        query_result.single_dataset_query_result.dataset_name = dataset_name

        if sql_queries:
            await stream_dynamic_message(
                f"create a 1 to 2 sentence message saying that here are the generated SQL queries and now let's execute them: {sql_queries}",
                config,
            )

            sql_results: list[SqlQueryInfo] = []
            for q, exp in zip(sql_queries, explanations):
                try:
                    full_result_data = await execute_sql(query=q)
                    result_data = truncate_if_too_large(full_result_data)
                    sql_results.append(
                        SqlQueryInfo(
                            sql_query=q,
                            explanation=exp,
                            sql_query_result=result_data,
                            full_sql_result=full_result_data,
                            success=True,
                            error=None,
                        )
                    )

                    await adispatch_custom_event(
                        "gopie-agent",
                        {
                            "content": "SQL queries executed",
                            "name": SQL_QUERIES_GENERATED,
                            "values": {SQL_QUERIES_GENERATED_ARG: sql_queries},
                        },
                    )
                except Exception as err:
                    error_str = str(err)
                    sql_results.append(
                        SqlQueryInfo(
                            sql_query=q,
                            explanation=exp,
                            sql_query_result=None,
                            success=False,
                            error=error_str,
                        )
                    )

            query_result.single_dataset_query_result.sql_results = sql_results

            return {
                "messages": [AIMessage(content=json.dumps(query_result.to_dict(), indent=2))],
                "query_result": query_result,
            }

        else:
            query_result.single_dataset_query_result.response_for_non_sql = response_for_non_sql

            await adispatch_custom_event(
                "gopie-agent",
                {
                    "content": response.user_friendly_response or "No SQL query generated",
                },
            )

            return {
                "messages": [AIMessage(content=json.dumps(query_result.to_dict(), indent=2))],
                "query_result": query_result,
            }

    except Exception as e:
        error_message = f"Error processing query: {str(e)}"
        query_result.single_dataset_query_result.error = error_message

        return {
            "messages": [
                AIMessage(
                    content=(
                        f"I'm sorry, but I encountered an error while "
                        f"processing your query: {error_message}"
                    )
                )
            ],
            "query_result": query_result,
        }
