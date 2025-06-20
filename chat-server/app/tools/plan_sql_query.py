import json
from typing import Any

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.tools import tool

from app.utils.langsmith.prompt_manager import get_prompt


@tool
async def plan_sql_query(
    user_query: str,
    schemas: list[dict] | None = None,
    unorganised_dataset_info: Any | None = None,
) -> dict:
    """
    Plan a SQL query given a user natural language query and dataset schemas.

    Situation to use this tool:
        - You already have the schemas of the datasets or related sufficient
          information from previous messages or the user already provided that
          for which the user is asking the query. Than you can directly plan
          the query by using this tool.

    IMPORTANT:
        - Pass atleast one of the schemas or unorganised_dataset_info.

    Args:
        user_query: The natural language query from the user.
        schemas: List of dataset schema dicts with table and column details.
        unorganised_dataset_info: If you don't have the schema of the datasets
                                  in an organised manner,

    Returns:
        A dict with keys:
            reasoning: explanation of thought process
            sql_queries: list of SQL queries to execute
            formatted_sql_queries: list of formatted SQL for UI
            tables_used: list of tables used
            expected_result: description of expected results
            limitations: any assumptions or limitations
    """
    try:
        from app.utils.model_registry.model_provider import get_custom_model

        if schemas:
            formatted_schemas = json.dumps(schemas, indent=2)
        else:
            formatted_schemas = unorganised_dataset_info

        prompt = get_prompt(
            "plan_query",
            user_query=user_query,
            formatted_datasets=formatted_schemas,
            error_context=None,
            dataset_analysis_context=None,
            node_messages_context=None,
        )

        llm = get_custom_model(model_id="o4-mini")

        response = await llm.ainvoke(prompt)
        content = (
            response.content if hasattr(response, "content") else str(response)
        )

        parser = JsonOutputParser()
        parsed = parser.parse(str(content))
        return parsed
    except Exception as e:
        return {"error": str(e), "user_query": user_query}


def get_dynamic_tool_text(args: dict) -> str:
    uq = args.get("user_query", "")
    return f"Planning SQL query for: {uq[:50]}"


__tool__ = plan_sql_query
__tool_category__ = "Data Exploration"
__get_dynamic_tool_text__ = get_dynamic_tool_text
