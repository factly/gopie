import json
import logging
from typing import Any

from langchain_core.runnables import RunnableConfig

from app.models.message import AIMessage, ErrorMessage, FinalQueryOutput
from app.models.query import QueryResult
from app.utils.model_provider import model_provider
from app.workflow.graph.types import State


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

        logging.info(
            f"query_result: {json.dumps(query_result.to_dict(), indent=2)}"
        )

    any_data_query = False
    if isinstance(query_result, QueryResult) and query_result.has_subqueries():
        for subquery in query_result.subqueries:
            if subquery.query_type == "data_query" and subquery.query_result:
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
    tool_results = []

    if query_result.has_subqueries():
        for subquery in query_result.subqueries:
            if subquery.tool_used_result:
                tool_results.append(subquery.tool_used_result)

    prompt = f"""
    User Query: "{user_query}"
    Available Context: {
        json.dumps(tool_results, indent=2)
        if tool_results
        else "No additional context available."
    }

    Instructions:
    - Incorporate tool results naturally if relevant
    - Preserve crucial information but present it clearly
    - Respond professionally and warmly
    - Keep response concise (3-5 sentences) unless detailed explanation needed
    - Focus on direct, helpful answers
    """

    llm = model_provider(config=config).get_llm()
    response = await llm.ainvoke({"input": prompt})

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
    results = []
    summary = []
    tool_used_results = []
    sql_with_explanations = []
    errors = []

    if query_result.has_subqueries():
        for subquery in query_result.subqueries:
            if subquery.query_result:
                results.append(subquery.query_result)

            if subquery.summary:
                summary.append(subquery.summary)

            if subquery.tool_used_result:
                tool_used_results.append(subquery.tool_used_result)

            if subquery.error_message:
                errors.extend(subquery.error_message)

            if subquery.sql_query_used:
                explanation = (
                    subquery.sql_query_explanation
                    if hasattr(subquery, "sql_query_explanation")
                    and subquery.sql_query_explanation
                    else "No explanation provided"
                )
                sql_with_explanations.append(
                    f"SQL: {subquery.sql_query_used}\n"
                    f"Explanation: {explanation}"
                )

    if not results and not tool_used_results:
        return await _handle_empty_results(query_result, errors, config)

    prompt = f"""
    Context:
    - Original User Query: "{user_query}"
    - SQL Queries with Explanations:
      {
          " ".join(sql_with_explanations)
          if sql_with_explanations
          else "No SQL queries were executed."
      }
    - Results: {json.dumps(results, indent=2)}
    - Summary: {json.dumps(summary, indent=2)}
    - Tool Results: {
        json.dumps(tool_used_results, indent=2)
        if tool_used_results
        else "No additional context available."
    }

    Instructions:
        1. You are answering: "{user_query}"
        2. Provide direct, concise answers based on the available data,
           but don't mention that you got information from SQL query results.
           You should directly answer the original user query.
        3. Present key insights first
        4. Format numbers properly (1,000,000, ₹, etc.)
        5. Include trends and patterns for financial/statistical data
        6. Use clear comparative language
        7. Only use facts from query results
        8. If there were errors in some parts of the query,
           acknowledge them briefly but focus on the data that was
         successfully retrieved
        9. Be transparent about limitations caused by errors without
        being negative
        10. If the data seems insufficient to fully answer the query,
        clearly state what aspects you can answer and what remains unclear
    """

    llm = model_provider(config=config).get_llm()
    response = await llm.ainvoke({"input": prompt})

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
    errors: Any,
    config: RunnableConfig,
) -> dict[str, list[Any]]:
    """
    Handle empty query results with a more personalized response
    """

    user_query = query_result.original_user_query

    prompt = f"""
    The user asked: "{user_query}"

    I need to inform them that I couldn't find any matching data in a
    helpful way.

    Errors that occurred:
    {errors}

    Instructions:
    1. Be empathetic but professional
    2. Specifically mention their query topic
    3. Suggest 2-3 possible alternative approaches or related questions they
       might try
    4. If there were errors, briefly acknowledge them without technical details
    """

    llm = model_provider(config=config).get_llm()
    response = await llm.ainvoke({"input": prompt})

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
