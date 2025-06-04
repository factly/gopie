import json

from langchain_core.callbacks.manager import adispatch_custom_event
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnableConfig

from app.models.message import ErrorMessage, IntermediateStep
from app.models.query import SqlQueryInfo
from app.utils.langsmith.prompt_manager import get_prompt
from app.utils.model_registry.model_provider import (
    get_chat_history,
    get_llm_for_node,
)
from app.workflow.graph.multidataset_agent.types import State


async def plan_query(state: State, config: RunnableConfig) -> dict:
    """
    Plan the SQL query based on user input and dataset information.
    This function generates a SQL query or multiple queries that address
    the user's question using the available dataset information.

    It will generate:
    - A single SQL query with JOINs if datasets are related
    - Multiple SQL queries if datasets are not related

    Args:
        state: The current state containing datasets, user query, and other
        context

    Returns:
        Updated state with the planned SQL query/queries
    """
    try:
        identified_datasets = state.get("identified_datasets", [])
        query_index = state.get("subquery_index", 0)
        user_query = (
            state.get("subqueries")[query_index]
            if state.get("subqueries")
            else "No input"
        )
        query_result = state.get("query_result", {})
        datasets_info = state.get("datasets_info", {})

        if not identified_datasets:
            raise Exception("No dataset selected for query planning")

        retry_count = query_result.subqueries[query_index].retry_count
        error_messages = query_result.subqueries[query_index].error_message
        node_messages = query_result.subqueries[query_index].node_messages

        if not identified_datasets:
            raise Exception("No dataset selected for query planning")

        if not datasets_info:
            raise Exception(
                "Could not get preview information for any of the selected "
                "datasets"
            )

        # TEMP
        formatted_datasets = json.dumps(datasets_info, indent=2)

        error_context = ""
        if error_messages and retry_count > 1:
            error_context = f"""
Previous attempt failed with this error:
{error_messages}

Please fix the issues in the query and try again. This is attempt
{retry_count} of 3.
"""

        dataset_analysis_context = ""
        if datasets_info.get("correct_column_requirements"):
            dataset_analysis_context = f"""
Analysis of column values from database:
{json.dumps(datasets_info.get("correct_column_requirements"), indent=2)}

IMPORTANT: Utilize these analyzed column values when constructing your
query, especially for matching conditions. This represents actual
values found or not found in the database.
"""

        node_messages_context = ""
        if node_messages:
            node_messages_context = f"""
Previous workflow steps information:
{json.dumps(node_messages, indent=2)}

Use this information to better understand the context and reasoning
from previous steps.
"""

        llm_prompt = get_prompt(
            "plan_query",
            user_query=user_query,
            formatted_datasets=formatted_datasets,
            error_context=error_context,
            dataset_analysis_context=dataset_analysis_context,
            node_messages_context=node_messages_context,
        )

        llm = get_llm_for_node("plan_query", config)
        response = await llm.ainvoke(
            {"chat_history": get_chat_history(config), "input": llm_prompt}
        )
        response_content = str(response.content)

        parser = JsonOutputParser()
        try:
            parsed_response = parser.parse(response_content)

            sql_queries = parsed_response.get("sql_queries", None)
            formatted_sql_queries = []
            sql_queries_info = []

            if not sql_queries:
                raise Exception("Failed in parsing SQL query/queries")

            for sql_query in sql_queries:
                sql_query_explanation = sql_query.get("explanation", "")
                sql_queries_info.append(
                    SqlQueryInfo(
                        sql_query=sql_query["sql_query"],
                        explanation=sql_query_explanation,
                    )
                )

                formatted_sql_queries.append(sql_query["formatted_sql_query"])

            query_result.subqueries[query_index].sql_queries = sql_queries_info

            # Extract additional details for node_messages
            reasoning = parsed_response.get("reasoning", "")
            limitations = parsed_response.get("limitations", "")

            tables_used = []
            for query in sql_queries:
                if "tables_used" in query:
                    tables_used.extend(query["tables_used"])

            query_result.set_node_message(
                "plan_query",
                {
                    "query_strategy": (
                        "single_query"
                        if len(sql_queries) == 1
                        else "multiple_queries"
                    ),
                    "tables_used": list(set(tables_used)),
                    "query_count": len(sql_queries),
                    "reasoning": reasoning,
                    "limitations": limitations,
                },
            )

            await adispatch_custom_event(
                "dataful-agent",
                {
                    "content": "Generated SQL query",
                    "queries": formatted_sql_queries,
                },
            )

            return {
                "query_result": query_result,
                "messages": [IntermediateStep.from_json(parsed_response)],
            }

        except Exception as parse_error:
            raise Exception(
                f"Failed to parse LLM response: {parse_error!s}"
            ) from parse_error

    except Exception as e:
        query_result.add_error_message(str(e), "Error in query planning")
        error_msg = f"Unexpected error in query planning: {e!s}"

        await adispatch_custom_event(
            "dataful-agent",
            {
                "content": "Error in query planning",
                "query": None,
            },
        )

        return {
            "query_result": query_result,
            "messages": [ErrorMessage.from_json({"error": error_msg})],
        }
