import json
from typing import Any, Dict, List

from src.lib.config.langchain_config import lc
from src.lib.graph.query_result.query_type import QueryResult
from src.lib.graph.types import AIMessage, ErrorMessage, State


def generate_result(state: State) -> Dict[str, List[Any]]:
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
            _handle_data_query(state, query_result)
            if any_data_query
            else _handle_conversational_query(state, query_result)
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


def _handle_conversational_query(
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

    return {"messages": [AIMessage(content=str(lc.llm.invoke(prompt).content))]}


def _handle_data_query(state: State, query_result: QueryResult) -> Dict[str, List[Any]]:
    """Handle data analysis queries"""
    if query_result.has_error():
        error_details = (
            json.dumps(query_result.error_message)
            if query_result.error_message
            else "Unknown error"
        )
        return {
            "messages": [ErrorMessage.from_text(json.dumps({"error": error_details}))]
        }

    user_query = query_result.original_user_query
    results = []
    tool_used_results = []
    sql_queries = []

    if query_result.has_subqueries():
        for subquery in query_result.subqueries:
            if subquery.query_result:
                results.append(subquery.query_result)

            if subquery.tool_used_result:
                tool_used_results.append(subquery.tool_used_result)

            if subquery.sql_query_used:
                sql_queries.append(subquery.sql_query_used)

    if not results and not tool_used_results:
        return _handle_empty_results()

    prompt = f"""
    Context:
    - Query: "{user_query}"
    - SQL: "{"; ".join(sql_queries)}"
    - Results: {json.dumps(results, indent=2)}
    - Tool Results: {json.dumps(tool_used_results, indent=2) if tool_used_results else "No additional context available."}

    Instructions:
        1. Provide direct, concise answers
        2. Present key insights first
        3. Format numbers properly (1,000,000, ₹, etc.)
        4. Include trends and patterns for financial/statistical data
        5. Use clear comparative language
        6. Only use facts from query results
    """

    return {"messages": [AIMessage(content=str(lc.llm.invoke(prompt).content))]}


def _handle_empty_results() -> Dict[str, List[Any]]:
    """Handle empty query results"""
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
