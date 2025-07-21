from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnableConfig

from app.models.message import ErrorMessage, IntermediateStep
from app.models.query import QueryResult, ToolUsedResult
from app.tool_utils.tool_node import has_tool_calls
from app.tool_utils.tools import ToolNames
from app.utils.langsmith.prompt_manager import get_prompt
from app.utils.model_registry.model_provider import get_model_provider
from app.workflow.events.event_utils import configure_node
from app.workflow.graph.multi_dataset_graph.types import State


@configure_node(
    role="intermediate",
    progress_message="Analyzing query...",
)
async def analyze_query(state: State, config: RunnableConfig) -> dict:
    query_result = state.get("query_result")
    query_index = state.get("subquery_index", -1)
    tool_call_count = state.get("tool_call_count", 0)

    # Check tool call limit
    if tool_call_count >= 5:
        return _create_error_response(
            query_result,
            "Maximum tool call limit reached (5 calls)",
            "analyze_query",
        )

    if _should_add_new_subquery(state, query_result, query_index):
        query_index += 1
        user_input = _get_user_input(state, query_index)

        query_result.add_subquery(
            query_text=user_input,
            sql_queries=[],
            query_info={
                "query_type": "conversational",
                "tables_used": None,
                "tool_used_result": None,
                "confidence_score": 5,
                "node_messages": {},
            },
        )
    else:
        user_input = _get_user_input(state, query_index)

    collect_and_store_tool_messages(query_result, query_index, state)

    if not user_input or user_input == "No input":
        return _create_error_response(query_result, "No user query provided", "analyze_query")

    try:
        tools_results = query_result.subqueries[query_index].tool_used_result

        prompt = get_prompt(
            "analyze_query",
            user_query=user_input,
            tool_results=tools_results,
            tool_call_count=tool_call_count,
            dataset_ids=state.get("dataset_ids", []),
            project_ids=state.get("project_ids", []),
        )

        tools_names = [
            ToolNames.EXECUTE_SQL_QUERY,
            ToolNames.GET_TABLE_SCHEMA,
            ToolNames.PLAN_SQL_QUERY,
        ]

        llm = get_model_provider(config).get_llm_with_tools("analyze_query", tools_names)
        response = await llm.ainvoke(prompt)

        if has_tool_calls(response):
            return _handle_tool_call_response(response, query_result, query_index, tool_call_count)
        else:
            return _handle_analysis_response(response, query_result, query_index, tool_call_count)

    except Exception as e:
        error_msg = f"Error analyzing query: {e!s}"
        query_result.add_error_message(str(e), "Error analyzing query")
        query_result.subqueries[query_index].query_type = "conversational"
        query_result.subqueries[query_index].confidence_score = 3

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
    if state.get("tool_call_count", 0) >= 5 and has_tool_calls(state["messages"][-1]):
        return "basic_conversation"

    last_message = state["messages"][-1]
    if has_tool_calls(last_message):
        return "tools"

    query_result = state.get("query_result")
    query_index = state.get("subquery_index")

    query_type = query_result.subqueries[query_index].query_type
    confidence_score = query_result.subqueries[query_index].confidence_score

    if query_type == "conversational":
        return "basic_conversation" if confidence_score >= 7 else "identify_datasets"
    else:
        return "identify_datasets"


def _get_user_input(state: State, query_index: int) -> str:
    subqueries = state.get("subqueries", [])
    if subqueries and 0 <= query_index < len(subqueries):
        return subqueries[query_index]
    return "No input"


def _should_add_new_subquery(state: State, query_result: QueryResult, query_index: int) -> bool:
    subqueries = state.get("subqueries", [])

    if query_index == -1 or not query_result.subqueries:
        return True

    if query_index + 1 < len(subqueries):
        next_query = subqueries[query_index + 1]
        last_recorded_query = query_result.subqueries[-1].query_text
        return next_query != last_recorded_query

    return False


def _create_error_response(
    query_result: QueryResult, error_msg: str, node_name: str = "analyze_query"
) -> dict:
    query_result.add_error_message(error_msg, node_name)
    error_data = {"error": error_msg, "is_data_query": False}

    return {
        "query_result": query_result,
        "query_type": "conversational",
        "messages": [ErrorMessage.from_json(error_data)],
    }


def _handle_tool_call_response(
    response: Any,
    query_result: QueryResult,
    query_index: int,
    tool_call_count: int,
) -> dict:
    query_result.subqueries[query_index].query_type = "conversational"

    ai_message = response if isinstance(response, BaseMessage) else AIMessage(content=str(response))

    return {
        "query_result": query_result,
        "subquery_index": query_index,
        "tool_call_count": tool_call_count + 1,
        "messages": [ai_message],
    }


def _handle_analysis_response(
    response: Any,
    query_result: QueryResult,
    query_index: int,
    tool_call_count: int,
) -> dict:
    parser = JsonOutputParser()
    response_content = str(response.content)
    parsed_content = parser.parse(response_content)

    query_type = parsed_content.get("query_type", "conversational")
    confidence_score = parsed_content.get("confidence_score", 5)
    reasoning = parsed_content.get("reasoning", "")
    clarification_needed = parsed_content.get("clarification_needed", "")

    query_result.subqueries[query_index].query_type = query_type
    query_result.subqueries[query_index].confidence_score = confidence_score
    query_result.set_node_message(
        "analyze_query",
        {
            "reasoning": reasoning,
            "clarification_needed": clarification_needed,
        },
    )

    return {
        "query_result": query_result,
        "subquery_index": query_index,
        "tool_call_count": tool_call_count,
        "messages": [IntermediateStep.from_json(parsed_content)],
    }


def collect_and_store_tool_messages(query_result: QueryResult, query_index: int, state: State):
    """
    Collect tool messages from state and store them in query result.
    """
    if query_index < 0 or query_index >= len(query_result.subqueries):
        return

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

    # Store tool messages if any were found
    if tool_messages:
        current_subquery = query_result.subqueries[query_index]
        if current_subquery.tool_used_result is None:
            current_subquery.tool_used_result = []
        current_subquery.tool_used_result.extend(tool_messages)
