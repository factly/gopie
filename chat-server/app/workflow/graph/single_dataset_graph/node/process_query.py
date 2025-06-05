import csv
import io
import json
from datetime import datetime
from typing import Any

from langchain_core.callbacks.manager import adispatch_custom_event
from langchain_core.messages import AIMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnableConfig

from app.services.gopie.dataset_info import get_dataset_info
from app.services.gopie.generate_schema import generate_schema
from app.services.gopie.sql_executor import execute_sql
from app.utils.model_registry.model_provider import (
    get_chat_history,
    get_llm_for_node,
)


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


async def process_query(state: Any, config: RunnableConfig) -> dict:
    """
    Process the user query for single dataset workflow:
    1. Get dataset schema and sample data
    2. Use LLM with DuckDB-specific prompt to generate SQL or text response
    3. Execute the SQL query if applicable
    4. Store results in query_result as dict
    5. Generate final user-friendly response
    """
    try:
        messages = state.get("messages", [])
        dataset_ids = state.get("dataset_ids", [])
        project_ids = state.get("project_ids", [])
        user_query = state.get("query", "")

        if not dataset_ids or not project_ids:
            raise Exception("No dataset or project ID provided")

        if not user_query and messages:
            last_message = messages[-1]
            if hasattr(last_message, "content"):
                user_query = str(last_message.content)
            elif isinstance(last_message, dict):
                user_query = last_message.get("content", "")

        dataset_id = dataset_ids[0]
        project_id = project_ids[0]

        dataset_details = await get_dataset_info(dataset_id, project_id)
        dataset_schema, sample_data = await generate_schema(
            dataset_details.name, limit=50
        )

        schema_json = json.dumps(dataset_schema, indent=2)
        rows_csv = convert_rows_to_csv(sample_data)

        prompt = f"""
You are a DuckDB and data expert. Review the user's question and respond
appropriately with a JSON response.

USER QUESTION: {user_query}

TABLE NAME: {dataset_details.name}

TABLE SCHEMA IN JSON:
---------------------
{schema_json}
---------------------

RANDOM 50 ROWS IN CSV:
---------------------
{rows_csv}
---------------------

RULES FOR SQL QUERIES:
- No semicolon at end of query
- Use double quotes for table/column names, single quotes for values
- Exclude rows with state='All India' when filtering/aggregating by state
- For share/percentage calculations, calculate as: (value/total)*100
- Exclude 'Total' category from categorical field calculations
- Include units/unit column when displaying value columns
- Use Levenshtein for fuzzy string matching
- Use ILIKE for case-insensitive matching
- Generate only read queries (SELECT)

RESPONSE FORMAT:
Return a JSON object with one of these formats:

For SQL queries:
{{
    "response_type": "sql",
    "sql_query": "<SQL query here without semicolon>",
    "explanation": "<Brief explanation of what the query does>"
}}

For non-SQL responses (like general questions):
{{
    "response_type": "text",
    "response": "<Your response here>",
    "explanation": "<Brief explanation if needed>"
}}

Always respond with valid JSON only.
        """

        llm = get_llm_for_node("plan_query", config)
        parser = JsonOutputParser()

        llm_response = await llm.ainvoke(
            {"input": prompt, "chat_history": get_chat_history(config)}
        )

        response_content = str(llm_response.content)
        parsed_response = parser.parse(response_content)

        if parsed_response.get("response_type") == "sql":
            sql_query = parsed_response.get("sql_query", "")
            explanation = parsed_response.get(
                "explanation", "SQL query generated from user request"
            )

            await adispatch_custom_event(
                "dataful-agent",
                {
                    "content": "SQL query generated",
                    "queries": [sql_query],
                },
            )

            try:
                query_result_data = await execute_sql(sql_query)

                sql_result = {
                    "sql_query": sql_query,
                    "explanation": explanation,
                    "result": query_result_data,
                    "success": True,
                    "error": None,
                }
            except Exception as sql_error:
                sql_result = {
                    "sql_query": sql_query,
                    "explanation": explanation,
                    "result": None,
                    "success": False,
                    "error": str(sql_error),
                }

            query_result = {
                "user_query": user_query,
                "dataset_name": dataset_details.name,
                "response_type": "sql",
                "sql_queries": [sql_result],
                "timestamp": datetime.now().isoformat(),
                "success": sql_result["success"],
            }

            return {
                "messages": [
                    AIMessage(content=json.dumps(query_result, indent=2))
                ],
                "query_result": query_result,
            }

        else:
            text_response = parsed_response.get("response", "")
            explanation = parsed_response.get("explanation", "")

            query_result = {
                "user_query": user_query,
                "dataset_name": dataset_details.name,
                "response_type": "text",
                "response": text_response,
                "explanation": explanation,
                "timestamp": datetime.now().isoformat(),
                "success": True,
            }

            return {
                "messages": [AIMessage(content=text_response)],
                "query_result": query_result,
            }

    except Exception as e:
        error_message = f"Error processing query: {str(e)}"
        error_result = {
            "user_query": user_query if "user_query" in locals() else "",
            "error": error_message,
            "success": False,
            "timestamp": datetime.now().isoformat(),
        }

        return {
            "messages": [
                AIMessage(
                    content=(
                        f"I'm sorry, but I encountered an error while "
                        f"processing your query: {error_message}"
                    )
                )
            ],
            "query_result": error_result,
        }
