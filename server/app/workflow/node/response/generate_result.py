import json
from typing import Any, Dict, List

from server.app.core.langchain_config import lc
from server.app.models.types import AIMessage, ErrorMessage, QueryResult
from server.app.workflow.graph.types import State


async def generate_result(state: State) -> Dict[str, List[Any]]:
    """Generate results of the executed query."""
    query_result = state.get("query_result")
    if query_result:
        print("\n" + "=" * 50)
        print("AGGREGATED QUERY RESULT")
        print("=" * 50)
        print(
            json.dumps(
                query_result.to_dict()
                if hasattr(query_result, "to_dict")
                else query_result,
                indent=2,
            )
        )
        print("=" * 50 + "\n")

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
                    ErrorMessage.from_text(
                        json.dumps(
                            {
                                "error": "Invalid query result format",
                                "details": "Expected QueryResult object",
                            }
                        )
                    )
                ]
            }

        return (
            await _handle_data_query(state, query_result)
            if any_data_query
            else await _handle_conversational_query(state, query_result)
        )
    except Exception as e:
        return {
            "messages": [
                ErrorMessage.from_text(
                    json.dumps(
                        {
                            "error": "Critical error in result generation",
                            "details": str(e),
                        }
                    )
                )
            ]
        }


async def _handle_conversational_query(
    state: State, query_result: QueryResult
) -> Dict[str, List[Any]]:
    """Handle conversational or tool-only queries"""
    user_query = query_result.original_user_query
    tool_results = []

    if query_result.has_subqueries():
        for subquery in query_result.subqueries:
            if subquery.tool_used_result:
                tool_results.append(subquery.tool_used_result)

    prompt = f"""
    User Query: "{user_query}"
    Available Context: {json.dumps(tool_results, indent=2) if tool_results else "No additional context available."}

    Instructions:
    - Incorporate tool results naturally if relevant
    - Preserve crucial information but present it clearly
    - Respond professionally and warmly
    - Keep response concise (3-5 sentences) unless detailed explanation needed
    - Focus on direct, helpful answers
    """

    response = await lc.llm.ainvoke(prompt)

    return {"messages": [AIMessage(content=str(response.content))]}


async def _handle_data_query(state: State, query_result: QueryResult) -> Dict[str, List[Any]]:
    """Handle data analysis queries"""
    user_query = query_result.original_user_query
    results = []
    tool_used_results = []
    sql_with_explanations = []
    errors = query_result.error_message

    if query_result.has_subqueries():
        for subquery in query_result.subqueries:
            if subquery.query_result:
                results.append(subquery.query_result)

            if subquery.tool_used_result:
                tool_used_results.append(subquery.tool_used_result)

            if subquery.sql_query_used:
                explanation = (
                    subquery.sql_query_explanation
                    if hasattr(subquery, "sql_query_explanation")
                    and subquery.sql_query_explanation
                    else "No explanation provided"
                )
                sql_with_explanations.append(
                    f"SQL: {subquery.sql_query_used}\nExplanation: {explanation}"
                )

    if not results and not tool_used_results:
        return await _handle_empty_results(user_query, errors)

    prompt = f"""
    Context:
    - Original User Query: "{user_query}"
    - SQL Queries with Explanations:
      {" ".join(sql_with_explanations) if sql_with_explanations else "No SQL queries were executed."}
    - Results: {json.dumps(results, indent=2)}
    - Tool Results: {json.dumps(tool_used_results, indent=2) if tool_used_results else "No additional context available."}
    - Errors encountered: {json.dumps(errors, indent=2) if errors else "No errors encountered."}

    Instructions:
        1. You are answering: "{user_query}"
        2. Provide direct, concise answers based on the available data, but don't mention that you got information from SQL query results. You should directly answer the original user query.
        3. Present key insights first
        4. Format numbers properly (1,000,000, ₹, etc.)
        5. Include trends and patterns for financial/statistical data
        6. Use clear comparative language
        7. Only use facts from query results
        8. If there were errors in some parts of the query, acknowledge them briefly but focus on the data that was successfully retrieved
        9. Be transparent about limitations caused by errors without being negative
        10. If the data seems insufficient to fully answer the query, clearly state what aspects you can answer and what remains unclear
    """

    response = await lc.llm.ainvoke(prompt)

    return {"messages": [AIMessage(content=str(response.content))]}


async def _handle_empty_results(
    user_query: str = "", errors: Any = None
) -> Dict[str, List[Any]]:
    """Handle empty query results with a more personalized response"""
    prompt = f"""
    The user asked: "{user_query}"

    I need to inform them that I couldn't find any matching data in a helpful way.

    Instructions:
    1. Be empathetic but professional
    2. Specifically mention their query topic
    3. Suggest 2-3 possible alternative approaches or related questions they might try
    4. If there were errors, briefly acknowledge them without technical details
    """

    if not user_query:
        return {
            "messages": [
                AIMessage(
                    content=(
                        "I analyzed your query but couldn't find matching data. This could be because:\n"
                        "- The data isn't in our current datasets\n"
                        "- The query needs rephrasing\n"
                        "- Specific filters might be excluding all results\n\n"
                        "Could you try rephrasing your question or asking about a different aspect?"
                    )
                )
            ]
        }

    response = await lc.llm.ainvoke(prompt)

    return {"messages": [AIMessage(content=str(response.content))]}
