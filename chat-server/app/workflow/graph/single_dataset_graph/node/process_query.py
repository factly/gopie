import csv
import io
import json
from datetime import datetime

from langchain_core.callbacks.manager import adispatch_custom_event
from langchain_core.messages import AIMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnableConfig

from app.core.constants import SQL_QUERIES_GENERATED
from app.services.gopie.sql_executor import execute_sql
from app.services.qdrant.get_schema import get_schema_from_qdrant
from app.utils.langsmith.prompt_manager import get_prompt
from app.utils.model_registry.model_provider import get_model_provider
from app.workflow.events.event_utils import configure_node
from app.workflow.graph.single_dataset_graph.types import State
from app.models.query import QueryResult, SingleDatasetQueryResult, SqlQueryInfo


def convert_rows_to_csv(rows: list[dict]) -> str:
    """
    Convert a list of dictionaries into a CSV-formatted string with special handling for certain cell values.
    
    Each row in the output CSV includes a "row_num" column as the first field. Cell values are converted as follows: `None` becomes "NULL", empty strings become "EMPTY_STRING", strings containing only whitespace become "WHITESPACE_ONLY", and numeric zeros become "0". Returns an empty string if the input list is empty.
    
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
    
    This asynchronous function orchestrates the workflow for handling a user query: it retrieves dataset schema and sample data, constructs prompts for a language model, parses the model's response for SQL queries and explanations, executes the queries if present, and compiles the results into a structured response. If no SQL queries are generated, it returns the non-SQL response from the model. Errors encountered during processing are captured and included in the result.
    
    Returns:
        dict: A dictionary containing a list of AIMessage objects with the serialized query result and the structured query result object.
    """
    user_query = state.get("user_query", "") or ""
    dataset_id = state.get("dataset_id", None)
    validation_result = state.get("validation_result", None)
    prev_query_result = state.get("query_result", None)

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
        sample_data = await execute_sql(query=sample_data_query)

        rows_csv = convert_rows_to_csv(sample_data)  # type: ignore

        prompt_messages = get_prompt(
            "process_query",
            user_query=user_query,
            dataset_name=dataset_name,
            dataset_schema=dataset_schema,
            rows_csv=rows_csv,
            prev_query_result=prev_query_result,
            validation_result=validation_result,
        )

        llm = get_model_provider(config).get_llm_for_node("process_query")
        parser = JsonOutputParser()

        llm_response = await llm.ainvoke(prompt_messages)

        response_content = str(llm_response.content)
        parsed_response = parser.parse(response_content)

        sql_queries = parsed_response.get("sql_queries", [])
        explanations = parsed_response.get("explanations", [])
        response_for_non_sql = parsed_response.get("response_for_non_sql", "")

        query_result.single_dataset_query_result.user_friendly_dataset_name = (
            user_provided_dataset_name
        )
        query_result.single_dataset_query_result.dataset_name = dataset_name

        if sql_queries:
            await adispatch_custom_event(
                "gopie-agent",
                {
                    "content": "SQL queries generated",
                    "name": SQL_QUERIES_GENERATED,
                    "values": {"queries": sql_queries},
                },
            )

            sql_results: list[SqlQueryInfo] = []

            for q, exp in zip(sql_queries, explanations):
                try:
                    result_data = await execute_sql(query=q)
                    sql_results.append(
                        SqlQueryInfo(
                            sql_query=q,
                            explanation=exp,
                            sql_query_result=result_data,
                            success=True,
                            error=None,
                        )
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
                "messages": [AIMessage(content=json.dumps(query_result, indent=2))],
                "query_result": query_result,
            }

        else:
            query_result.single_dataset_query_result.response_for_non_sql = response_for_non_sql

            return {
                "messages": [AIMessage(content=json.dumps(query_result, indent=2))],
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
