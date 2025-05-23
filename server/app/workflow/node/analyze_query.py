from typing import Any

from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnableConfig

from app.models.message import ErrorMessage, IntermediateStep
from app.tools.tool_node import has_tool_calls
from app.utils.model_registry.model_provider import get_llm_for_node
from app.workflow.graph.types import State
from app.workflow.prompts.prompt_selector import get_prompt


async def analyze_query(state: State, config: RunnableConfig) -> dict:
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
            sql_queries=[],
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

        prompt = get_prompt(
            "analyze_query",
            user_query=user_input,
            tool_results=tools_results,
        )
        llm = get_llm_for_node("analyze_query", config, with_tools=True)
        response: Any = await llm.ainvoke({"input": prompt})
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
