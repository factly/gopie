from langchain_core.messages import AIMessage, BaseMessage, ToolCall
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnableConfig

from app.core.constants import (
    DATASETS_USED,
    DATASETS_USED_ARG,
    SQL_QUERIES_GENERATED,
    SQL_QUERIES_GENERATED_ARG,
    VISUALIZATION_RESULT,
    VISUALIZATION_RESULT_ARG,
)
from app.core.log import logger
from app.utils.langsmith.prompt_manager import get_prompt
from app.utils.model_registry.model_provider import (
    get_chat_history,
    get_model_provider,
)
from app.workflow.events.event_utils import configure_node

from ..types import AgentState


def get_all_tool_calls(chat_history: list[BaseMessage]) -> list[ToolCall]:
    tool_calls = []
    for message in chat_history:
        if isinstance(message, AIMessage) and message.tool_calls:
            tool_calls.extend(message.tool_calls)
    return tool_calls


def get_sql_queries(tool_calls: list[ToolCall]) -> list[str]:
    sql_queries = []
    for tool_call in tool_calls:
        if tool_call.get("name") == SQL_QUERIES_GENERATED:
            args = tool_call.get("args", {})
            sql_queries.extend(args.get(SQL_QUERIES_GENERATED_ARG, []))
    return sql_queries


def get_datasets_used(tool_calls: list[ToolCall]) -> list[str]:
    datasets_used = []
    for tool_call in tool_calls:
        if tool_call.get("name") == DATASETS_USED:
            args = tool_call.get("args", {})
            datasets_used.append(args.get(DATASETS_USED_ARG, []))
    return datasets_used


def get_vizpaths(tool_calls: list[ToolCall]) -> list[str]:
    vizpaths = []
    for tool_call in tool_calls:
        if tool_call.get("name") == VISUALIZATION_RESULT:
            args = tool_call.get("args", {})
            vizpaths.extend(args.get(VISUALIZATION_RESULT_ARG, []))
            break
    return vizpaths


def format_chat_history(chat_history: list[BaseMessage]) -> str:
    formatted_chat_history = ""
    if chat_history:
        formatted_chat_history = "\n".join(
            [
                (
                    f"User: {message.content}"
                    if message.type == "human"
                    else f"Assistant: {message.content}"
                )
                for message in chat_history
            ]
        )
        tool_calls = get_all_tool_calls(chat_history)
        sql_queries = get_sql_queries(tool_calls)
        formatted_chat_history += f"\n\n Previous SQL Queries: {sql_queries}\n\n"
    return formatted_chat_history


def get_last_vizpaths(chat_history: list[BaseMessage]) -> list[str]:
    tool_calls = get_all_tool_calls(chat_history)
    vizpaths = get_vizpaths(tool_calls)
    return vizpaths


def get_previous_datasets_ids(chat_history: list[BaseMessage]) -> list[str]:
    tool_calls = get_all_tool_calls(chat_history)
    datasets_ids = get_datasets_used(tool_calls)
    return datasets_ids


@configure_node(
    role="intermediate",
    progress_message="Processing chat context...",
)
async def process_context(state: AgentState, config: RunnableConfig) -> dict:
    user_input = state.get("initial_user_query", "")
    chat_history = get_chat_history(config) or []
    formatted_chat_history = format_chat_history(chat_history)
    last_vizpaths = get_last_vizpaths(chat_history)
    relevant_datasets_ids = get_previous_datasets_ids(chat_history)

    prompt_messages = get_prompt(
        "process_context",
        current_query=user_input,
        formatted_chat_history=formatted_chat_history,
    )

    llm = get_model_provider(config).get_llm_for_node("process_context")
    response = await llm.ainvoke(prompt_messages)

    try:
        parser = JsonOutputParser()
        parsed_response = parser.parse(str(response.content))

        is_follow_up = parsed_response.get("is_follow_up", False)
        is_new_data_needed = parsed_response.get("is_new_data_needed", False)
        needs_visualization = parsed_response.get("is_visualization_query", False)
        relevant_sql_queries = parsed_response.get("relevant_sql_queries", [])
        enhanced_query = parsed_response.get("enhanced_query", user_input)
        context_summary = parsed_response.get("context_summary", "")
        if is_follow_up:
            final_query = f"""
            This is a follow-up question to a previous query.

            User Query: {enhanced_query}

            Context Summary: {context_summary}
            """
        else:
            final_query = enhanced_query
        return {
            "user_query": final_query,
            "new_data_needed": is_new_data_needed,
            "needs_visualization": needs_visualization,
            "relevant_datasets_ids": relevant_datasets_ids,
            "relevant_sql_queries": relevant_sql_queries,
            "enhanced_query": enhanced_query,
            "previous_json_paths": last_vizpaths,
        }

    except Exception as e:
        logger.error(f"Error processing context: {e!s}")
        return {
            "user_query": user_input,
            "new_data_needed": True,
            "needs_visualization": False,
            "relevant_datasets_ids": relevant_datasets_ids,
            "relevant_sql_queries": [],
            "enhanced_query": user_input,
            "previous_json_paths": last_vizpaths,
        }
