from langchain_core.callbacks.manager import adispatch_custom_event
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from app.utils.langsmith.prompt_manager import get_prompt_llm_chain


@tool
async def plan_sql_query(
    user_query: str,
    dataset_info: str,
    config: RunnableConfig,
    status_message: str = "",
) -> dict:
    """
    Plan a (only single) SQL query given a user natural language query and dataset schemas.

    Prerequisite:
        - You should already have the schemas of the datasets
        - Or required dataset schema is present when you called the `get_datasets_schemas` tool

    ONLY use this tool when:
        - If the user wants summary or statistics or summary of the data.
        - If the user query can be answered with a simple single SQL query.

    Args:
        user_query: The natural language query from the user.
        dataset_info: The information about the datasets that the user provided or you got from
                      previous tool or already have it.

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
        response = await chain.ainvoke({"user_query": user_query, "dataset_info": dataset_info})
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
    return args.get("status_message") or "Using SQL query planner tool to plan the query..."


__tool__ = plan_sql_query
__tool_category__ = "Data Exploration"
__should_display_tool__ = True
__get_dynamic_tool_text__ = get_dynamic_tool_text
