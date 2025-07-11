from langchain_core.callbacks.manager import adispatch_custom_event
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from app.core.constants import SQL_QUERIES_GENERATED
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
        prompt = get_prompt("plan_sql_query_tool", user_query=user_query, schemas=schemas)
        model_id = get_node_model("plan_sql_query_tool")
        llm = get_model_provider(config).get_llm(model_id=model_id)
        response = await llm.ainvoke(prompt)
        content = response.content if hasattr(response, "content") else str(response)

        parser = JsonOutputParser()
        parsed = parser.parse(str(content))

        sql_queries = parsed.get("sql_queries", [])

        await adispatch_custom_event(
            "gopie-agent",
            {
                "content": "SQL query planning tool",
                "name": SQL_QUERIES_GENERATED,
                "values": {"queries": sql_queries},
            },
        )

        return parsed
    except Exception as e:
        await adispatch_custom_event(
            "gopie-agent",
            {
                "content": "Error in query planning tool",
            },
        )
        return {"error": str(e), "user_query": user_query}


def get_dynamic_tool_text(args: dict) -> str:
    uq = args.get("user_query", "")
    return f"Planning SQL query for: {uq[:50]}"


__tool__ = plan_sql_query
__tool_category__ = "Data Exploration"
__should_display_tool__ = True
__get_dynamic_tool_text__ = get_dynamic_tool_text
