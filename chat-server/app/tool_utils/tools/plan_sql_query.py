from langchain_core.callbacks.manager import adispatch_custom_event
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from app.utils.langsmith.prompt_manager import get_prompt_llm_chain


@tool
async def plan_sql_query(
    user_query: str,
    schemas: list[dict],
    config: RunnableConfig,
) -> dict:
    """
    Plan a SQL query given a user natural language query and dataset schemas.

    ONLY use this tool when:
        - You already have the schemas of the datasets or related sufficient
          information from previous messages or the user already provided that
          for which the user is asking the query. Than you can directly plan
          the query by using this tool.

    DO NOT use this tool when:
        - If the above condition is not true.
        - If you want information about the dataset.
          Because further steps already have full workflow to get the
          information and then process it.

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
        chain = get_prompt_llm_chain("plan_sql_query_tool", config)
        response = await chain.ainvoke({"user_query": user_query, "schemas": schemas})
        return response
    except Exception as e:
        await adispatch_custom_event(
            "gopie-agent",
            {
                "content": "Error in query planning tool",
            },
        )
        return {"error": str(e), "user_query": user_query}


def get_dynamic_tool_text(args: dict) -> str:
    uq = (args.get("user_query") or "").strip().replace("\n", " ")
    if len(uq) > 70:
        uq = uq[:67] + "..."
    schemas = args.get("schemas") or []
    num_tables = len(schemas)
    suffix = f" using {num_tables} schema(s)" if num_tables else ""
    return f"Planning SQL{suffix}: {uq}" if uq else f"Planning SQL{suffix}"


__tool__ = plan_sql_query
__tool_category__ = "Data Exploration"
__should_display_tool__ = True
__get_dynamic_tool_text__ = get_dynamic_tool_text
