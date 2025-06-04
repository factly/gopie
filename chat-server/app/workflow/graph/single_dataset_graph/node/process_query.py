import json
from datetime import datetime
from typing import Any

from langchain_core.messages import AIMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnableConfig

from app.services.gopie.dataset_info import get_dataset_info
from app.services.gopie.generate_schema import generate_schema
from app.services.gopie.sql_executor import execute_sql
from app.utils.langsmith.prompt_manager import get_prompt
from app.utils.model_registry.model_provider import (
    get_chat_history,
    get_llm_for_node,
)


async def process_query(state: Any, config: RunnableConfig) -> dict:
    """
    Process the user query for single dataset workflow:
    1. Get dataset schema and sample data
    2. Use LLM to generate SQL query based on user question
    3. Execute the SQL query
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
            dataset_details.name
        )

        formatted_dataset_info = {
            "dataset_name": dataset_details.name,
            "schema": dataset_schema,
            "sample_data": (sample_data[:5] if sample_data else []),
        }

        plan_prompt = get_prompt(
            "plan_query",
            user_query=user_query,
            formatted_datasets=json.dumps(formatted_dataset_info, indent=2),
            error_context="",
            dataset_analysis_context="",
            node_messages_context="",
        )

        llm = get_llm_for_node("plan_query", config)
        parser = JsonOutputParser()

        plan_response = await llm.ainvoke(
            {"input": plan_prompt, "chat_history": get_chat_history(config)}
        )

        plan_content = str(plan_response.content)
        parsed_plan = parser.parse(plan_content)

        sql_results = []
        sql_queries = parsed_plan.get("sql_queries", [])

        for sql_query_data in sql_queries:
            sql_query = sql_query_data.get("sql_query", "")
            explanation = sql_query_data.get("explanation", "")

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

            sql_results.append(sql_result)

        query_result = {
            "user_query": user_query,
            "dataset_name": dataset_details.name,
            "sql_queries": sql_results,
            "timestamp": datetime.now().isoformat(),
            "success": any(result["success"] for result in sql_results),
        }

        return {
            "messages": [
                AIMessage(content=json.dumps(query_result, indent=2))
            ],
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
