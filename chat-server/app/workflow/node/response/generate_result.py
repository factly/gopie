import json
from typing import Any

from langchain_core.runnables import RunnableConfig

from app.core.log import logger
from app.models.message import AIMessage, ErrorMessage, FinalQueryOutput
from app.models.query import QueryResult
from app.utils.model_registry.model_provider import (
    get_chat_history,
    get_llm_for_node,
)
from app.workflow.graph.types import State
from app.workflow.prompts.generate_result_prompt import (
    create_conversational_query_prompt,
    create_data_query_prompt,
    create_empty_results_prompt,
)


async def generate_result(
    state: State, config: RunnableConfig
) -> dict[str, list[Any]]:
    """
    Generate a response based on the query result
    """

    query_result = state.get("query_result")
    if query_result:
        if isinstance(query_result, QueryResult):
            query_result.calculate_execution_time()

        logger.debug(
            f"query_result: {json.dumps(query_result.to_dict(), indent=2)}"
        )

    any_data_query = False
    if isinstance(query_result, QueryResult) and query_result.has_subqueries():
        for subquery in query_result.subqueries:
            if subquery.query_type == "data_query":
                any_data_query = True
                break

    try:
        if not isinstance(query_result, QueryResult):
            return {
                "messages": [
                    ErrorMessage.from_json(
                        {
                            "error": "Invalid query result format",
                            "details": "Expected QueryResult object",
                        }
                    )
                ]
            }

        return (
            await _handle_data_query(query_result, config)
            if any_data_query
            else await _handle_conversational_query(query_result, config)
        )
    except Exception as e:
        return {
            "messages": [
                ErrorMessage.from_json(
                    {
                        "error": "Critical error in result generation",
                        "details": str(e),
                    }
                )
            ]
        }


async def _handle_conversational_query(
    query_result: QueryResult,
    config: RunnableConfig,
) -> dict[str, list[Any]]:
    """
    Handle conversational or tool-only queries
    """

    user_query = query_result.original_user_query

    prompt = create_conversational_query_prompt(
        user_query=user_query, query_result=query_result
    )

    llm = get_llm_for_node("generate_result", config)
    response = await llm.ainvoke(
        {"input": prompt, "chat_history": get_chat_history(config)}
    )

    return {
        "messages": [
            AIMessage(
                content=[
                    FinalQueryOutput(
                        result=str(response.content),
                        execution_time=query_result.execution_time,
                    ).to_dict()
                ]
            )
        ]
    }


async def _handle_data_query(
    query_result: QueryResult,
    config: RunnableConfig,
) -> dict[str, list[Any]]:
    """
    Handle data analysis queries
    """

    user_query = query_result.original_user_query

    has_results = False
    if query_result.has_subqueries():
        for subquery in query_result.subqueries:
            for sql_query_info in subquery.sql_queries:
                if sql_query_info.sql_query_result:
                    has_results = True
                    break
            if has_results:
                break

    if not has_results:
        return await _handle_empty_results(query_result, config)

    prompt = create_data_query_prompt(
        user_query=user_query, query_result=query_result
    )

    llm = get_llm_for_node("generate_result", config)
    response = await llm.ainvoke(
        {"input": prompt, "chat_history": get_chat_history(config)}
    )

    return {
        "messages": [
            AIMessage(
                content=[
                    FinalQueryOutput(
                        result=str(response.content),
                        execution_time=query_result.execution_time,
                    ).to_dict()
                ]
            )
        ]
    }


async def _handle_empty_results(
    query_result: QueryResult,
    config: RunnableConfig,
) -> dict[str, list[Any]]:
    """
    Handle empty query results with a more personalized response
    """

    user_query = query_result.original_user_query

    prompt = create_empty_results_prompt(
        user_query=user_query, query_result=query_result
    )

    llm = get_llm_for_node("generate_result", config)
    response = await llm.ainvoke(
        {"input": prompt, "chat_history": get_chat_history(config)}
    )

    return {
        "messages": [
            AIMessage(
                content=[
                    FinalQueryOutput(
                        result=str(response.content),
                        execution_time=query_result.execution_time,
                    ).to_dict()
                ]
            )
        ]
    }
