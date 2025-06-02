from langchain_core.callbacks.manager import adispatch_custom_event
from langchain_core.messages import AIMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnableConfig

from app.core.log import logger
from app.utils.model_registry.model_provider import (
    get_chat_history,
    get_llm_for_node,
)
from app.workflow.graph.types import State
from app.workflow.prompts.stream_updates_prompt import (
    create_execution_analysis_prompt,
    create_stream_update_prompt,
)


async def stream_updates(state: State, config: RunnableConfig) -> dict:
    query_result = state.get("query_result", None)
    query_index = state.get("subquery_index", 0)

    stream_update_prompt = create_stream_update_prompt(
        query_result=query_result,
        query_index=query_index,
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

    analysis_prompt = create_execution_analysis_prompt(
        last_stream_message_content=last_stream_message.content
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
