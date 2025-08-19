from datetime import datetime
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnableConfig

from app.models.message import ErrorMessage, IntermediateStep
from app.models.query import QueryResult, ToolUsedResult
from app.tool_utils.tool_node import has_tool_calls
from app.tool_utils.tools import ToolNames
from app.utils.langsmith.prompt_manager import get_prompt_llm_chain
from app.workflow.events.event_utils import (
    configure_node,
    fake_streaming_response,
)
from app.workflow.graph.multi_dataset_graph.types import State


@configure_node(
    role="intermediate",
    progress_message="Analyzing query...",
)
async def analyze_query(state: State, config: RunnableConfig) -> dict:
    tool_call_count = state.get("tool_call_count", 0)
    query_result = state.get(
        "query_result",
        QueryResult(
            original_user_query=state.get("user_query", ""),
            timestamp=datetime.now(),
            execution_time=0,
            subqueries=[],
        ),
    )
    user_input = state.get("user_query")

    analyze_result = query_result.analyze_query_result

    if tool_call_count >= 5:
        return _create_error_response(query_result, "Maximum tool call limit reached (5 calls)")

    if not user_input:
        return _create_error_response(query_result, "No user query provided")

    collect_and_store_tool_messages(query_result, state)

    try:
        chain_input = {
            "user_query": user_input,
            "tool_results": analyze_result.tool_used_result,
            "tool_call_count": tool_call_count,
            "dataset_ids": state.get("dataset_ids", []),
            "project_ids": state.get("project_ids", []),
        }

        tools_names = [
            ToolNames.EXECUTE_SQL_QUERY,
            ToolNames.GET_TABLE_SCHEMA,
            ToolNames.LIST_DATASETS,
            ToolNames.PLAN_SQL_QUERY,
        ]

        chain = get_prompt_llm_chain("analyze_query", config, tool_names=tools_names)
        response = await chain.ainvoke(chain_input)

        if has_tool_calls(response):
            return await _handle_tool_call_response(response, query_result, tool_call_count)
        else:
            return await _handle_analysis_response(response, query_result, tool_call_count, config)

    except Exception as e:
        return _create_error_response(
            query_result, f"Error analyzing query: {e!s}", tool_call_count
        )


def route_from_analysis(state: State) -> str:
    """
    Route to the appropriate next node based on query analysis

    Args:
        state: Current state with analysis results

    Returns:
        String name of the next node to route to
    """
    # Check if we've reached the tool call limit
    last_message = state["messages"][-1]
    if state.get("tool_call_count", 0) >= 5 and has_tool_calls(last_message):
        return "basic_conversation"

    if has_tool_calls(last_message):
        return "tools"

    query_result = state.get("query_result")
    analyze_result = query_result.analyze_query_result

    query_type = analyze_result.query_type
    confidence_score = analyze_result.confidence_score

    if query_type == "conversational":
        return "basic_conversation" if confidence_score >= 7 else "generate_subqueries"
    else:
        return "generate_subqueries"


def _create_error_response(
    query_result: QueryResult, error_msg: str, tool_call_count: int = 0
) -> dict:
    analyze_result = query_result.analyze_query_result
    analyze_result.query_type = "conversational"
    analyze_result.confidence_score = 3
    analyze_result.response = error_msg

    return {
        "query_result": query_result,
        "tool_call_count": tool_call_count,
        "messages": [ErrorMessage(content=error_msg)],
    }


async def _handle_tool_call_response(
    response: Any,
    query_result: QueryResult,
    tool_call_count: int,
) -> dict:
    ai_message = response if isinstance(response, BaseMessage) else AIMessage(content=str(response))

    return {
        "query_result": query_result,
        "tool_call_count": tool_call_count + 1,
        "messages": [ai_message],
    }


async def _handle_analysis_response(
    response: Any,
    query_result: QueryResult,
    tool_call_count: int,
    config: RunnableConfig,
) -> dict:
    parser = JsonOutputParser()
    response_content = str(response.content)
    parsed_content = parser.parse(response_content)

    query_type = parsed_content.get("query_type", "conversational")
    confidence_score = parsed_content.get("confidence_score", 5)
    reasoning = parsed_content.get("reasoning", "")
    clarification_needed = parsed_content.get("clarification_needed", "")
    status_message = parsed_content.get("status_message", "")

    analyze_result = query_result.analyze_query_result
    analyze_result.query_type = query_type
    analyze_result.confidence_score = confidence_score
    analyze_result.response = (
        f"\nReasoning: {reasoning} \n\n Clarification: {clarification_needed}".strip()
    )

    result = {
        "query_result": query_result,
        "tool_call_count": tool_call_count,
        "messages": [IntermediateStep(content=analyze_result.response)],
    }

    if status_message:
        await fake_streaming_response(status_message, config)

    return result


def collect_and_store_tool_messages(query_result: QueryResult, state: State):
    """
    Collect tool messages from state and store them in query result.
    """
    tool_messages = []
    messages = state.get("messages", [])

    # Collect tool messages from the end of the message list
    for msg in reversed(messages):
        if isinstance(msg, ToolMessage):
            tool_messages.append(
                ToolUsedResult(
                    tool_call_id=msg.tool_call_id,
                    content=str(msg.content),
                    name=getattr(msg, "name", None),
                )
            )
        else:
            break

    if tool_messages:
        analyze_result = query_result.analyze_query_result
        if analyze_result.tool_used_result is None:
            analyze_result.tool_used_result = []
        analyze_result.tool_used_result.extend(tool_messages)
