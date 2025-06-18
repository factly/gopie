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
from app.utils.model_registry.model_provider import (
    get_chat_history,
    get_llm_for_node,
)
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


async def process_query(state: State, config: RunnableConfig) -> dict:
    try:
        dataset_ids = state.get("dataset_ids", [])
        user_query = state.get("user_query", "")
        retry_count = state.get("retry_count", 0)
        error = state.get("error")
        failed_queries = state.get("failed_queries", [])

        dataset_id = dataset_ids[0] if dataset_ids else None
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

        prompt = f"""
You are a DuckDB and data expert. Analyze the user's question and determine
if you need to generate SQL queries to get new data or if you can answer using
available context.

USER QUESTION: {user_query}

TABLE NAME: {dataset_name} (This is the name of the table in the database
                            so use this in forming SQL queries)

TABLE SCHEMA IN JSON:
---------------------
{schema_json}
---------------------

SAMPLE DATA (50 ROWS) IN CSV:
---------------------
{rows_csv}
---------------------

{error_context}

INSTRUCTIONS:
1. If the user's question can be answered using the sample data or previous
   context, generate a response with empty SQL queries and give response for
   non-sql queries.
2. If new data analysis is needed, generate appropriate SQL queries

RULES FOR SQL QUERIES (when needed):
- No semicolon at end of query
- Use double quotes for table/column names, single quotes for values
- Exclude rows with state='All India' when filtering/aggregating by state
- For share/percentage calculations, calculate as: (value/total)*100
- Exclude 'Total' category from categorical field calculations
- Include units/unit column when displaying value columns
- Use Levenshtein for fuzzy string matching
- Use ILIKE for case-insensitive matching
- Generate only read queries (SELECT)
- Pay careful attention to exact column names from the schema

RESPONSE FORMAT:
Return a JSON object in one of these formats:
{{
    "sql_queries": ["<SQL query here without semicolon>", ...],
    "explanations": ["<Brief explanation for each query>", ...],
    "response_for_non_sql": "<Brief explanation for non-sql response>"
}}

Always respond with valid JSON only.
        """

        llm = get_llm_for_node("process_query", config)
        parser = JsonOutputParser()

        llm_response = await llm.ainvoke(
            {"input": prompt, "chat_history": get_chat_history(config)}
        )

        response_content = str(llm_response.content)
        parsed_response = parser.parse(response_content)

        sql_queries = parsed_response.get("sql_queries", [])
        explanations = parsed_response.get("explanations", [])
        response_for_non_sql = parsed_response.get("response_for_non_sql", "")
        current_failed_queries = []

        if sql_queries:
            await adispatch_custom_event(
                "dataful-agent",
                {
                    "content": "SQL queries generated",
                    "queries": sql_queries,
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

    return "check_visualization"
