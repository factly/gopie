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
    - Answer the query directly and confidently without mentioning your
      information sources
    - Seamlessly integrate relevant information from tool results
      when applicable
    - Respond in a friendly, professional, and conversational tone
    - Be concise but thorough - prioritize accuracy over brevity
    - Use simple language and avoid technical jargon unless appropriate
    - Personalize your response based on the specific query context
    - If uncertain about specific details, acknowledge limitations clearly
    - Format information for maximum readability with lists or bullet points
      when appropriate
    - NEVER make up or fabricate data when you encounter errors or missing info
    - When there are errors in data retrieval, clearly indicate that info
      couldn't be retrieved without showing technical error details
    - If data is unavailable, suggest alternative questions the user might ask
    - Do not output technical details like SQL queries or error codes
    """

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
    results = []
    tool_used_results = []
    sql_with_explanations = []
    errors = []

    if query_result.has_subqueries():
        for subquery in query_result.subqueries:
            for sql_query_info in subquery.sql_queries:
                if sql_query_info.sql_query_result:
                    results.append(sql_query_info.sql_query_result)

                sql_with_explanations.append(
                    f"SQL: {sql_query_info.sql_query}\n"
                    f"Explanation: {sql_query_info.explanation}\n"
                    f"Result: {sql_query_info.sql_query_result}\n"
                    f"Summary: {sql_query_info.summary}\n"
                )
            if subquery.tool_used_result:
                tool_used_results.append(subquery.tool_used_result)

            if subquery.error_message:
                errors.extend(subquery.error_message)

    if not results and not tool_used_results:
        return await _handle_empty_results(query_result, errors, config)

    prompt = f"""
    Context:
    - Original User Query: "{user_query}"
    - SQL Queries with Explanations:
      {sql_with_explanations}
    - Results: {json.dumps(results, indent=2)}
    - Tool Results: {
        json.dumps(tool_used_results, indent=2)
        if tool_used_results
        else "No additional context available."
    }

    Instructions:
    1. Answer the user's query directly and with confidence, avoiding phrases
       like "based on the data" or "according to the results"
    2. Start with the most important insights and key findings that directly
       address "{user_query}"
    3. Format numerical data properly with appropriate separators
       (e.g., 1,000,000) and currency symbols when relevant
    4. Highlight trends, patterns, and comparisons when present in the data
    5. Use simple, clear language that a non-technical audience can understand
    6. Organize information logically with natural transitions between
       related points
    7. For financial or statistical data, include brief interpretations
       of what the numbers signify
    8. Be precise and factual - only state what is explicitly supported
       by the data
    9. If some portions of the data were unavailable due to errors, focus on
       delivering value from the available information
    10. When appropriate, conclude with the most meaningful insight or takeaway
    11. From the subqueries that outputted summaries, give a brief extract of
        the most important insights
    12. NEVER make up or fabricate data that isn't explicitly in the results
        (provide the actual data in form of context)
    13. If there are errors or missing data, clearly acknowledge this without
        showing technical error details
    14. Do not output technical details like SQL queries or error codes
    """

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
    errors: Any,
    config: RunnableConfig,
) -> dict[str, list[Any]]:
    """
    Handle empty query results with a more personalized response
    """

    user_query = query_result.original_user_query

    prompt = f"""
    The user asked: "{user_query}"

    Any errors that occurred while executing the query: {errors}

    Instructions:
    1. Acknowledge that no matching data was found for their specific query
    2. Be empathetic but confident in your response, maintaining a helpful tone
    3. Briefly mention the essence of their query to personalize the response
    4. If errors occurred during processing, acknowledge them in general terms
       without technical details
    5. Suggest 2-3 specific alternative approaches or related questions they
       might try instead
    6. Phrase your suggestions as actionable recommendations
    7. Avoid apologies - instead, focus on providing alternative paths forward
    8. Keep your response concise and constructive
    9. NEVER make up or fabricate data, especially when errors have occurred
    10. Clearly inform the user that the requested information couldn't be
        retrieved without exposing technical error details
    11. Do not output technical details like SQL queries or error codes
    """

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
