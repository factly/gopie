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
    """
    Process the user query for single dataset workflow:
    1. Get dataset schema and sample data
    2. Use LLM with DuckDB-specific prompt to generate SQL or text response
    3. Execute the SQL query if applicable
    4. Store results in query_result as dict
    5. Generate final user-friendly response
    """
    try:
        dataset_ids = state.get("dataset_ids", [])
        user_query = state.get("user_query", "")

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

        prompt = f"""
You are a DuckDB and data expert. Review the user's question and respond
appropriately with a JSON response.

USER QUESTION: {user_query}

TABLE NAME: {dataset_name} (This is the name of the table in the database
                            so use this in forming SQL queries)

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
Return a JSON object in one of these formats:

For SQL queries (single or multiple):
{{
    "response_type": "sql",
    "sql_queries": ["<SQL query here without semicolon>", ...],
    "explanations": ["<Brief explanation for each query>", ...]
}}

For non-SQL responses:
{{
    "response_type": "text",
    "response": "<Your response here>",
    "explanation": "<Brief explanation if needed>"
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

        if parsed_response.get("response_type") == "sql":
            sql_queries = parsed_response.get("sql_queries", [])
            explanations = parsed_response.get("explanations", [])

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
                    sql_results.append(
                        {
                            "sql_query": q,
                            "explanation": exp,
                            "result": None,
                            "success": False,
                            "error": str(err),
                        }
                    )

            query_result = {
                "user_query": user_query,
                "user_friendly_dataset_name": user_provided_dataset_name,
                "dataset_name": dataset_name,
                "response_type": "sql",
                "sql_queries": sql_results,
                "timestamp": datetime.now().isoformat(),
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
                "user_friendly_dataset_name": user_provided_dataset_name,
                "dataset_name": dataset_name,
                "response_type": "text",
                "response": text_response,
                "explanation": explanation,
                "timestamp": datetime.now().isoformat(),
            }

            return {
                "messages": [AIMessage(content=text_response)],
                "query_result": query_result,
            }

    except Exception as e:
        error_message = f"Error processing query: {str(e)}"
        error_result = {
            "error": error_message,
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
