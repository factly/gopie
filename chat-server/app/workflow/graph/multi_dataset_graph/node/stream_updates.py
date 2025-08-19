import json

from langchain_core.language_models.fake_chat_models import (
    GenericFakeChatModel,
)
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from app.core.log import logger
from app.utils.langsmith.prompt_manager import get_prompt_llm_chain
from app.workflow.events.event_utils import configure_node
from app.workflow.graph.multi_dataset_graph.types import State


class StreamUpdateResponse(BaseModel):
    stream_update: str = Field(description="User-friendly message about the subquery execution")
    continue_execution: bool = Field(
        description="Whether to continue execution with remaining subqueries", default=True
    )


async def stream_updates(state: State, config: RunnableConfig) -> dict:
    query_result = state.get("query_result", None)
    query_index = state.get("subquery_index", 0)
    subqueries = state.get("subqueries", [])

    stream_message = ""
    continue_execution = False

    try:
        subquery_result = query_result.subqueries[query_index]

        remaining_index = query_index + 1
        remaining_subqueries = [sq for sq in subqueries[remaining_index:]]

        subquery_messages = f"""
            This is subquery {query_index + 1} / {len(subqueries)}:\n
            {subquery_result.query_text}\n\n

            Remaining subqueries:
            {remaining_subqueries}
        """

        chain_input = {
            "subquery_result": json.dumps(subquery_result.to_dict()),
            "original_user_query": query_result.original_user_query,
            "subquery_messages": subquery_messages,
        }

        chain = get_prompt_llm_chain(
            "stream_updates",
            config,
            schema=StreamUpdateResponse,
        )
        response = await chain.ainvoke(chain_input)

        stream_message = response.stream_update
        continue_execution = response.continue_execution
    except Exception as e:
        stream_message = "Something went wrong while generating the subquery response"
        logger.error(f"Error in stream_updates: {e}")

    return {
        "messages": [AIMessage(content=stream_message)],
        "subquery_index": query_index + 1,
        "continue_execution": continue_execution,
    }


@configure_node(
    role="ai",
    progress_message="",
)
async def check_further_execution_requirement(state: State, config: RunnableConfig) -> str:
    """
    Determines if further execution is required based on the continue_execution flag stored in state.
    Returns a string indicating the next step: "next_sub_query" or "end_execution".
    """

    continue_execution = state.get("continue_execution", True)
    last_message = state["messages"][-1]

    if isinstance(last_message, AIMessage):
        llm = GenericFakeChatModel(
            messages=iter([last_message]), metadata=config.get("metadata", {})
        )
        await llm.ainvoke(input=last_message.content, config=config)

    if continue_execution:
        return "next_sub_query"
    else:
        return "end_execution"
