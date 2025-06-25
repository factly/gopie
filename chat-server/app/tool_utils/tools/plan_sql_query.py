import json

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.tools import tool

from app.utils.model_registry.model_provider import get_custom_model


def get_sql_planning_prompt(user_query: str, formatted_schemas: str) -> str:
    return f"""You are an expert SQL analyst. Given a user's natural language
query and dataset schemas, plan the appropriate SQL queries to answer their
question.

USER QUERY: {user_query}

AVAILABLE DATASETS AND SCHEMAS:
{formatted_schemas}

INSTRUCTIONS:
1. Analyze the user query to understand what data they need
2. Examine the provided schemas to identify relevant tables and columns
3. Use the actual dataset names (like 'gq_xxxxx') from the schema in your SQL,
   NOT the user-friendly display names
4. Plan the SQL query/queries needed to answer the question
5. Consider joins, aggregations, filters, and ordering as needed
6. Provide clear reasoning for your approach

OUTPUT FORMAT (JSON):
{{
    "reasoning": "Step-by-step explanation of your thought process",
    "sql_queries": ["list of executable SQL queries"],
    "tables_used": ["list of table names used"],
    "expected_result": "description of what the query results contain",
    "limitations": "any assumptions, limitations, or considerations"
}}

CRITICAL: Always use the actual dataset name field from the schema in your
SQL queries, never use display names or titles. Look for fields like
"dataset_name" or similar in the schema.

Ensure your SQL is syntactically correct and follows best practices. If
multiple queries are needed, explain the sequence and purpose of each."""


@tool
async def plan_sql_query(
    user_query: str,
    schemas: list[dict],
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
        if schemas:
            formatted_schemas = json.dumps(schemas, indent=2)

        prompt = get_sql_planning_prompt(user_query, formatted_schemas)

        llm = get_custom_model(model_id="gpt-4o")
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
