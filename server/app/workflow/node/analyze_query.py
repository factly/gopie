import json
from typing import Any

from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.output_parsers import JsonOutputParser

from app.core.langchain_config import lc
from app.models.message import ErrorMessage, IntermediateStep
from app.tools.tool_node import has_tool_calls
from app.workflow.graph.types import State


def create_llm_prompt(user_query: str, tool_results: list):
    return f"""
        You are an AI assistant specialized in data analysis.
        Your role is to help users analyze data by determining query types.

        USER QUERY:
        "{user_query}"

        TOOL RESULTS:
        {json.dumps(tool_results)}

        INSTRUCTIONS:
        1. Classify this query into ONE of these types:
            - "data_query": Requires SQL execution on datasets
            (e.g., analysis, trends, statistics, filtered data)
            - "conversational": General conversation not requiring
                                data or tools
            - "tool_only": Can be answered using available tools without SQL

        2. For data queries:
            - These require accessing and analyzing datasets with SQL
            - Examples: "Show me sales trends",
              "What's the average price?", "Compare metrics across regions"

        3. For conversational queries:
            - General questions, greetings, or casual conversation
            - No dataset analysis or tools required

        4. For tool-only queries:
            - If the query can be answered directly with
              tool calls without dataset analysis, make those tool calls
            - Try to call all necessary tools at once to answer the query
            - Can be answered with tools but don't require SQL processing
            - Examples: Questions about available datasets, \
              schema information, metadata, tool-specific questions or can be
              answered with the available tools

        If there is a need of calling a tool to answer the query,
        please call the tool(s) and dont return in the requested format
        and directly make a tool call

        RESPONSE FORMAT:
        Respond in this JSON format:
        {{
            "query_type": "data_query|conversational|tool_only",
            "reasoning": "Clear explanation of classification decision",
            "data_query": true|false,
        }}
        """


async def analyze_query(state: State) -> dict:
    """
    Analyze the user query and the identified datasets to determine:
    1. If this is a data query requiring dataset processing
    2. If this is a conversational query needing no datasets
    3. If this is a tool-only query that can be handled without SQL execution

    Args:
        state: The current state object containing messages and tool results

    Returns:
        Query type and call tools if needed to answer user query or
        identify datasets if it is a data query
    """
    last_message = state["messages"][-1]
    query_result = state.get("query_result")

    tool_call_count = state.get("tool_call_count", 0)

    # Check if we've reached the maximum allowed tool calls
    if tool_call_count >= 5:
        error_msg = "Maximum tool call limit reached (5 calls)"
        query_result.add_error_message(error_msg, "analyze_query")

        return {
            "query_result": query_result,
            "query_type": "conversational",
            "messages": [
                ErrorMessage.from_json(
                    {"error": error_msg, "is_data_query": False}
                )
            ],
        }

    if isinstance(last_message, ToolMessage):
        query_index = state.get("subquery_index", -1)
        user_input = (
            state.get("subqueries", ["No input"])[query_index]
            if state.get("subqueries")
            else "No input"
        )
    else:
        query_index = state.get("subquery_index", -1) + 1
        user_input = (
            state.get("subqueries", ["No input"])[query_index]
            if state.get("subqueries")
            and query_index < len(state.get("subqueries", []))
            else "No input"
        )
        query_result.add_subquery(
            query_text=user_input,
            sql_query_used="",
            query_info={
                "query_type": "conversational",
                "tables_used": None,
                "query_result": None,
                "tool_used_result": None,
            },
        )

    tools_results = query_result.subqueries[query_index].tool_used_result

    try:
        if not user_input:
            query_result.add_error_message(
                "No user query provided", "analyze_query"
            )
            error_data = {
                "error": "No user query provided",
                "is_data_query": False,
            }
            return {
                "query_result": query_result,
                "query_type": "conversational",
                "messages": [ErrorMessage.from_json(error_data)],
            }

        prompt = create_llm_prompt(user_input, tools_results)
        response: Any = await lc.llm.ainvoke(prompt)
        parser = JsonOutputParser()

        if has_tool_calls(response):
            query_result.subqueries[query_index].query_type = "tool_only"

            tool_call_count += 1

            return {
                "query_result": query_result,
                "subquery_index": query_index,
                "tool_call_count": tool_call_count,
                "messages": [
                    (
                        response
                        if isinstance(response, AIMessage)
                        else AIMessage(content=str(response))
                    )
                ],
            }

        response_content = str(response.content)
        parsed_content = parser.parse(response_content)

        query_type = parsed_content.get("query_type", "conversational")
        query_result.subqueries[query_index].query_type = query_type

        return {
            "query_result": query_result,
            "subquery_index": query_index,
            "tool_call_count": tool_call_count,
            "messages": [IntermediateStep.from_json(parsed_content)],
        }

    except Exception as e:
        error_msg = f"Error analyzing query: {e!s}"
        query_result.add_error_message(str(e), "Error analyzing query")
        query_result.subqueries[query_index].query_type = "conversational"

        return {
            "query_result": query_result,
            "subquery_index": query_index,
            "tool_call_count": tool_call_count,
            "messages": [ErrorMessage.from_json({"error": error_msg})],
        }


def route_from_analysis(state: State) -> str:
    """
    Route to the appropriate next node based on query analysis

    Args:
        state: Current state with analysis results

    Returns:
        String name of the next node to route to
    """
    # Check if we've reached the tool call limit
    if state.get("tool_call_count", 0) >= 5 and has_tool_calls(
        state["messages"][-1]
    ):
        return "basic_conversation"

    last_message = state["messages"][-1]
    if has_tool_calls(last_message):
        return "tools"

    query_result = state.get("query_result")
    query_index = state.get("subquery_index")

    query_type = query_result.subqueries[query_index].query_type

    if query_type in {"conversational", "tool_only"}:
        return "basic_conversation"
    else:
        return "identify_datasets"
