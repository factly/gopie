from typing import Any

from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnableConfig

from app.models.message import ErrorMessage, IntermediateStep
from app.models.query import QueryResult
from app.tool_utils.tool_node import has_tool_calls
from app.tool_utils.tools import ToolNames
from app.utils.langsmith.prompt_manager import get_prompt
from app.utils.model_registry.model_provider import (
    get_chat_history,
    get_model_provider,
)
from app.workflow.events.event_utils import configure_node
from app.workflow.graph.multi_dataset_graph.types import State


@configure_node(
    role="intermediate",
    progress_message="Analyzing query...",
)
async def analyze_query(state: State, config: RunnableConfig) -> dict:
    """
    Analyze the user query and the identified datasets to determine:
    1. If this is a data query requiring dataset processing
    2. If this is a conversational query (may use tools but doesn't need
       datasets)

    Args:
        state: The current state object containing messages and tool results

    Returns:
        Query type and call tools if needed to answer user query or
        identify datasets if it is a data query
    """
    last_message = state["messages"][-1]
    query_result = state.get("query_result")
    subqueries = state.get("subqueries", [])
    query_index = state.get("subquery_index", -1)

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
        user_input = (
            state.get("subqueries", ["No input"])[query_index]
            if state.get("subqueries")
            else "No input"
        )

    add_new_subquery = (
        query_index == -1
        or subqueries[query_index] != query_result.subqueries[-1].query_text
    )

    if add_new_subquery:
        query_index += 1
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
                "confidence_score": 5,
                "node_messages": {},
            },
        )

    collect_and_store_tool_messages(query_result, query_index, state)
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

        chat_history = get_chat_history(config)
        prompt = get_prompt(
            "analyze_query",
            user_query=user_input,
            tool_results=tools_results,
            tool_call_count=tool_call_count,
            dataset_ids=state.get("dataset_ids", []),
            project_ids=state.get("project_ids", []),
            chat_history=chat_history,
        )
        tools_names = [
            ToolNames.EXECUTE_SQL_QUERY,
            ToolNames.GET_TABLE_SCHEMA,
            ToolNames.LIST_DATASETS,
            ToolNames.PLAN_SQL_QUERY,
        ]
        llm = get_model_provider(config).get_llm_with_tools(
            "analyze_query", tools_names
        )
        response: Any = await llm.ainvoke(prompt)
        parser = JsonOutputParser()

        if has_tool_calls(response):
            query_result.subqueries[query_index].query_type = "conversational"
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
        confidence_score = parsed_content.get("confidence_score", 5)
        reasoning = parsed_content.get("reasoning", "")
        clarification_needed = parsed_content.get("clarification_needed", "")

        query_result.subqueries[query_index].query_type = query_type
        query_result.subqueries[
            query_index
        ].confidence_score = confidence_score

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
    confidence_score = query_result.subqueries[query_index].confidence_score

    if query_type == "conversational":
        if confidence_score >= 8:
            return "basic_conversation"
        else:
            return "identify_datasets"
    else:
        return "identify_datasets"


def collect_and_store_tool_messages(
    query_result: QueryResult, query_index: int, state: State
):
    tool_messages = []
    messages = state.get("messages", [])

    for msg in reversed(messages):
        if isinstance(msg, ToolMessage):
            tool_messages.append(
                {
                    "tool_call_id": msg.tool_call_id,
                    "content": msg.content,
                    "name": getattr(msg, "name", None),
                    "type": "tool_message",
                }
            )
        else:
            break

    if (
        tool_messages
        and query_index >= 0
        and query_index < len(query_result.subqueries)
    ):
        if query_result.subqueries[query_index].tool_used_result is None:
            query_result.subqueries[query_index].tool_used_result = []
        elif not isinstance(
            query_result.subqueries[query_index].tool_used_result, list
        ):
            query_result.subqueries[query_index].tool_used_result = [
                query_result.subqueries[query_index].tool_used_result
            ]

        query_result.subqueries[query_index].tool_used_result.extend(
            tool_messages
        )
