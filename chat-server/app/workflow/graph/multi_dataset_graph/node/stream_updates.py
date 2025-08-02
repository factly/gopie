import json

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from app.core.log import logger
from app.utils.langsmith.prompt_manager import get_prompt
from app.utils.model_registry.model_provider import get_configured_llm_for_node
from app.workflow.events.event_utils import configure_node
from app.workflow.graph.multi_dataset_graph.types import State


class ExecutionAnalysisOutput(BaseModel):
    continue_execution: bool = Field(
        description="Whether to continue execution with remaining subqueries"
    )
    reasoning: str = Field(description="Brief explanation for the decision")


@configure_node(
    role="ai",
    progress_message="",
)
async def stream_updates(state: State, config: RunnableConfig) -> dict:
    query_result = state.get("query_result", None)
    query_index = state.get("subquery_index", 0)
    subqueries = state.get("subqueries", [])

    subquery_result = query_result.subqueries[query_index]

    remaining_index = query_index + 1
    remaining_subqueries = [sq for sq in subqueries[remaining_index:]]

    subquery_messages = f"""
        This is subquery {query_index + 1} / {len(subqueries)}:\n
        {subquery_result.query_text}\n\n

        Remaining subqueries:
        {remaining_subqueries}
    """

    stream_update_prompt = get_prompt(
        node_name="stream_updates",
        subquery_result=json.dumps(subquery_result.to_dict()),
        original_user_query=query_result.original_user_query,
        subquery_messages=subquery_messages,
    )

    llm = get_configured_llm_for_node("stream_updates", config)
    response = await llm.ainvoke(stream_update_prompt)

    return {"messages": [AIMessage(content=response.content)], "subquery_index": query_index + 1}


async def check_further_execution_requirement(state: State, config: RunnableConfig) -> str:
    """
    Determines if further execution is required based on the current state.
    Returns a string indicating the next step: "next_sub_query" or
    "end_execution".
    """

    last_stream_message = state.get("messages", [])[-1]

    analysis_prompt = get_prompt(
        node_name="execution_analysis",
        last_stream_message_content=last_stream_message.content,
    )

    llm = get_configured_llm_for_node(
        "check_further_execution_requirement", config, schema=ExecutionAnalysisOutput
    )
    response = await llm.ainvoke(analysis_prompt)

    try:
        logger.debug(f"Execution decision: {response.model_dump()}")
        continue_execution = response.continue_execution

        if continue_execution:
            return "next_sub_query"
        else:
            return "end_execution"
    except Exception as e:
        logger.error(f"Error processing LLM response: {str(e)}")
        return "end_execution"
