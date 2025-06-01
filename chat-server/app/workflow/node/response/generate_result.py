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

    prompt = f"""
You are generating the final response to a user query.
This is the LAST step in the workflow.

USER QUERY: "{user_query}"

QUERY RESULT:
{json.dumps(query_result.to_dict(), indent=2)}

RESPONSE INSTRUCTIONS:
1. Answer the query directly and confidently based on all available
   information
2. Do not mention how you processed the information or your sources
3. Use a friendly, professional tone as if speaking directly to the user
4. Seamlessly integrate all relevant information from the available context
5. Use bullet points or numbered lists when presenting multiple pieces of
   information
6. Highlight the most important or directly relevant information first
7. If the query could not be fully answered, clearly explain what
   information is available and what might be missing
8. NEVER fabricate data or make assumptions beyond what's provided in the
   context
9. If you encounter contradictory information, acknowledge it and provide
   the most reliable interpretation based on the available evidence
10. Format your response for maximum readability
11. NEVER mention technical implementation details such as SQL queries,
    error codes, or processing steps
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

    prompt = f"""
You are generating the final response to a data analysis query.
This is the LAST step in the workflow.

USER QUERY: "{user_query}"

QUERY RESULT:
{json.dumps(query_result.to_dict(), indent=2)}

RESPONSE INSTRUCTIONS:
1. Begin with a direct, confident answer to the user's query
2. Focus on presenting insights and conclusions from the data, not the
   process
3. Structure your response in a logical flow:
   - Main findings and direct answer to the query
   - Supporting details and evidence from the data
   - Any additional insights or patterns discovered
   - Implications or actionable recommendations (if appropriate)

4. For numerical data:
   - Format properly with appropriate separators (e.g., 1,000,000)
   - Use currency symbols when relevant
   - Present percentages with appropriate precision

5. When presenting complex information:
   - Use bullet points or numbered lists for clarity
   - Group related information together
   - Use brief, descriptive subheadings if needed

6. If the data reveals patterns or trends:
   - Highlight these clearly
   - Explain their significance in context
   - Avoid technical jargon when explaining their meaning

7. When data is incomplete or has limitations:
   - Acknowledge these limitations briefly without technical details
   - Focus on what CAN be concluded from the available data
   - Suggest alternative approaches if appropriate

8. IMPORTANT DON'Ts:
   - Do NOT mention SQL queries, data processing steps, or technical
     implementation
   - Do NOT use phrases like "based on the data" or "according to the
     results"
   - Do NOT fabricate data or draw conclusions beyond what the data
     supports
   - Do NOT include error messages or technical details

9. TONE:
   - Professional but conversational
   - Confident in presenting findings
   - Educational when explaining complex concepts
   - Neutral and objective when presenting facts
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
    config: RunnableConfig,
) -> dict[str, list[Any]]:
    """
    Handle empty query results with a more personalized response
    """

    user_query = query_result.original_user_query

    prompt = f"""
You are generating a response for a query that returned no results.
This is the LAST step in the workflow.

USER QUERY: "{user_query}"

QUERY RESULT:
{json.dumps(query_result.to_dict(), indent=2)}

RESPONSE INSTRUCTIONS:
1. Acknowledge that no matching data was found for their specific query
2. Begin with a clear, direct statement that addresses what the user was
   looking for
3. Analyze the execution details to understand where the process
   encountered issues
4. Provide a helpful, constructive response that offers:
   - A brief explanation of why their query might not have returned results
   - 2-3 specific alternative approaches they could try
   - Suggestions for modifying their query to get better results

5. Be empathetic but confident, maintaining a helpful tone
6. Avoid technical jargon and error details - focus on what the user can
   do next
7. Personalize your response by referencing elements of their original
   query
8. Frame alternatives as positive suggestions rather than focusing on
   what didn't work

9. DO NOT:
   - Apologize excessively
   - Show technical error messages or SQL queries
   - Make up data that doesn't exist
   - Use generic responses that don't address their specific query

10. End with an encouraging note that invites them to try a modified
    approach
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
