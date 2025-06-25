from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from app.utils.langsmith.prompt_manager import get_prompt
from app.utils.model_registry.model_provider import get_model_provider
from app.utils.model_registry.model_selection import get_node_model


@tool
async def plan_sql_query(
    user_query: str,
    schemas: list[dict],
    config: RunnableConfig,
) -> dict:
    """
    Plan a SQL query given a user natural language query and dataset schemas.

    Situation to use this tool:
        - You already have the schemas of the datasets or related sufficient
          information from previous messages or the user already provided that
          for which the user is asking the query. Than you can directly plan
          the query by using this tool.

    IMPORTANT:
        - Don't use this tool if the above situation is not true.

    Args:
        user_query: The natural language query from the user.
        schemas: List of dataset schema dicts with table and column details.
                Must include the actual dataset name field (e.g., 'gq_xxxxx')
                that should be used in SQL queries, not just display names.

    Returns:
        A dict with keys:
            reasoning: explanation of thought process
            sql_queries: the SQL queries ready for execution
            tables_used: list of tables used
            expected_result: description of expected results
            limitations: any assumptions or limitations
    """
    try:
        prompt = get_prompt(
            "sql_query_planning", user_query=user_query, schemas=schemas
        )
        model_id = get_node_model("plan_sql_query")
        llm = get_model_provider(config).get_llm(model_id=model_id)
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
__should_display_tool__ = True
__get_dynamic_tool_text__ = get_dynamic_tool_text
