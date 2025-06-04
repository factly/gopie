import json

from langchain_core.callbacks.manager import adispatch_custom_event
from langchain_core.messages import AIMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnableConfig

from app.core.log import logger
from app.utils.langsmith.prompt_manager import get_prompt
from app.utils.model_registry.model_provider import (
    get_chat_history,
    get_llm_for_node,
)
from app.workflow.graph.multi_dataset_graph.types import State


async def stream_updates(state: State, config: RunnableConfig) -> dict:
    query_result = state.get("query_result", None)
    query_index = state.get("subquery_index", 0)

    subquery_result = query_result.subqueries[query_index]
    sql_queries = [
        sql_info.sql_query for sql_info in subquery_result.sql_queries
    ]
    node_messages = subquery_result.node_messages

    remaining_index = query_index + 1
    remaining_subqueries = [
        sq.query_text for sq in query_result.subqueries[remaining_index:]
    ]

    stream_update_prompt = get_prompt(
        node_name="stream_updates",
        query_text=subquery_result.query_text,
        original_user_query=query_result.original_user_query,
        subquery_count=len(query_result.subqueries),
        query_index=query_index + 1,
        subquery_result=json.dumps(subquery_result.to_dict()),
        error_message=json.dumps(subquery_result.error_message),
        sql_queries=json.dumps(sql_queries),
        node_messages=json.dumps(node_messages),
        remaining_subqueries=json.dumps(remaining_subqueries),
    )

    llm = get_llm_for_node("stream_updates", config)
    response = await llm.ainvoke(
        {
            "input": stream_update_prompt,
            "chat_history": get_chat_history(config),
        }
    )

    logger.debug(f"Stream updates response: {response.content}")

    return {"messages": [AIMessage(content=response.content)]}


async def check_further_execution_requirement(
    state: State, config: RunnableConfig
) -> str:
    """
    Determines if further execution is required based on the current state.
    Returns a string indicating the next step: "next_sub_query" or
    "end_execution".
    """
    await adispatch_custom_event(
        "dataful-agent",
        {
            "content": "do not stream",
        },
    )

    last_stream_message = state.get("messages", [])[-1]

    analysis_prompt = get_prompt(
        node_name="execution_analysis",
        last_stream_message_content=last_stream_message.content,
    )

    llm = get_llm_for_node("check_further_execution_requirement", config)
    response = await llm.ainvoke(
        {
            "input": analysis_prompt,
            "chat_history": get_chat_history(config),
        }
    )

    await adispatch_custom_event(
        "dataful-agent",
        {
            "content": "continue streaming",
        },
    )

    try:
        result = JsonOutputParser().parse(str(response.content))
        logger.debug(f"Execution decision: {result}")
        continue_execution = result.get("continue_execution", False)

        if continue_execution:
            return "next_sub_query"
        else:
            return "end_execution"
    except Exception as e:
        logger.error(f"Error parsing LLM response: {str(e)}")
        return "end_execution"
