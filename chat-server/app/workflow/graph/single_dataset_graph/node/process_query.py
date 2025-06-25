import csv
import io
import json
from datetime import datetime

from langchain_core.callbacks.manager import adispatch_custom_event
from langchain_core.messages import AIMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnableConfig

from app.services.gopie.sql_executor import execute_sql
from app.services.qdrant.get_schema import get_schema_from_qdrant
from app.utils.langsmith.prompt_manager import get_prompt
from app.utils.model_registry.model_provider import (
    get_chat_history,
    get_model_provider,
)
from app.workflow.events.event_utils import configure_node
from app.workflow.graph.single_dataset_graph.types import State


def convert_rows_to_csv(rows: list[dict]) -> str:
    if not rows:
        return ""

    output = io.StringIO()
    writer = csv.writer(output)

    if rows:
        headers = list(rows[0].keys())
        writer.writerow(headers)

        for row in rows:
            record = [
                str(value) if value is not None else ""
                for value in row.values()
            ]
            writer.writerow(record)

    return output.getvalue()


@configure_node(
    role="intermediate",
    progress_message="Processing query...",
)
async def process_query(state: State, config: RunnableConfig) -> dict:
    try:
        dataset_id = state.get("dataset_id", None)
        user_query = state.get("user_query", "")
        retry_count = state.get("retry_count", 0)
        error = state.get("error")
        failed_queries = state.get("failed_queries", [])

        if not dataset_id:
            raise Exception("No dataset ID provided")

        schema_info = await get_schema_from_qdrant(dataset_id)
        if "error" in schema_info:
            raise Exception(f"Schema fetch error: {schema_info['error']}")

        dataset_name = schema_info.get("dataset_name", "")
        user_provided_dataset_name = schema_info.get("name", "")

        sample_data_query = f"SELECT * FROM {dataset_name} LIMIT 50"
        sample_data = await execute_sql(sample_data_query)

        schema_json = json.dumps(schema_info, indent=2)
        rows_csv = convert_rows_to_csv(sample_data)

        error_context = ""
        if retry_count > 0 and error and failed_queries:
            failed_queries_str = "\n".join(
                [
                    f"- Query: {fq['sql_query']}\n  Error: {fq['error']}"
                    for fq in failed_queries
                ]
            )
            error_context = f"""
PREVIOUS ATTEMPT FAILED:
Retry attempt: {retry_count}/3
Error: {error}
Failed queries:
{failed_queries_str}

Please analyze the error and generate corrected SQL queries.
- If the error is in the SQL execution error than try to generate sql queries
  that works on every sql engine.
"""

        prompt_messages = get_prompt(
            "process_query",
            user_query=user_query,
            dataset_name=dataset_name,
            schema_json=schema_json,
            rows_csv=rows_csv,
            error_context=error_context,
            chat_history=get_chat_history(config),
        )

        llm = get_model_provider(config).get_llm_for_node("process_query")
        parser = JsonOutputParser()

        llm_response = await llm.ainvoke(prompt_messages)

        response_content = str(llm_response.content)
        parsed_response = parser.parse(response_content)

        sql_queries = parsed_response.get("sql_queries", [])
        explanations = parsed_response.get("explanations", [])
        response_for_non_sql = parsed_response.get("response_for_non_sql", "")
        current_failed_queries = []

        if sql_queries:
            data_name = "sql_queries"
            data_args = {"queries": sql_queries}
            await adispatch_custom_event(
                "gopie-agent",
                {
                    "content": "SQL queries generated",
                    "name": data_name,
                    "values": data_args,
                },
            )

            sql_results = []

            for q, exp in zip(sql_queries, explanations):
                try:
                    result_data = await execute_sql(q)
                    sql_results.append(
                        {
                            "sql_query": q,
                            "explanation": exp,
                            "result": result_data,
                            "success": True,
                            "error": None,
                        }
                    )
                except Exception as err:
                    error_str = str(err)
                    sql_results.append(
                        {
                            "sql_query": q,
                            "explanation": exp,
                            "result": None,
                            "success": False,
                            "error": error_str,
                        }
                    )
                    current_failed_queries.append(
                        {"sql_query": q, "error": error_str}
                    )

            query_result = {
                "user_query": user_query,
                "user_friendly_dataset_name": user_provided_dataset_name,
                "dataset_name": dataset_name,
                "sql_queries": sql_results,
                "timestamp": datetime.now().isoformat(),
            }

            return {
                "messages": [
                    AIMessage(content=json.dumps(query_result, indent=2))
                ],
                "query_result": query_result,
                "retry_count": 0,
                "error": None,
                "failed_queries": current_failed_queries,
            }

        else:

            query_result = {
                "user_query": user_query,
                "user_friendly_dataset_name": user_provided_dataset_name,
                "dataset_name": dataset_name,
                "response_for_non_sql": response_for_non_sql,
                "timestamp": datetime.now().isoformat(),
            }

            return {
                "messages": [
                    AIMessage(content=json.dumps(query_result, indent=2))
                ],
                "query_result": query_result,
                "retry_count": 0,
                "error": None,
                "failed_queries": [],
            }

    except Exception as e:
        error_message = f"Error processing query: {str(e)}"
        retry_count = state.get("retry_count", 0)

        return {
            "messages": [
                AIMessage(
                    content=(
                        f"I'm sorry, but I encountered an error while "
                        f"processing your query: {error_message}"
                    )
                )
            ],
            "query_result": None,
            "retry_count": retry_count + 1,
            "error": error_message,
            "failed_queries": [],
        }


def should_retry(state: State) -> str:
    retry_count = state.get("retry_count", 0)
    error = state.get("error", None)
    failed_queries = state.get("failed_queries", [])

    if (error or failed_queries) and retry_count < 3:
        return "retry"
    else:
        return "response"
