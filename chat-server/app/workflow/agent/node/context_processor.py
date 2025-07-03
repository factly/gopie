from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnableConfig

from app.core.log import logger
from app.utils.langsmith.prompt_manager import get_prompt
from app.utils.model_registry.model_provider import (
    get_chat_history,
    get_model_provider,
)
from app.workflow.events.event_utils import configure_node

from ..types import AgentState


@configure_node(
    role="intermediate",
    progress_message="Processing chat context...",
)
async def process_context(state: AgentState, config: RunnableConfig) -> dict:
    messages = state.get("messages", [])

    if messages and isinstance(messages[-1], HumanMessage):
        user_input = str(messages[-1].content)
    else:
        raise Exception("Last Message must be a user message")

    chat_history = get_chat_history(config)
    if not chat_history:
        return {"user_query": user_input}

    prompt_messages = get_prompt(
        "process_context",
        current_query=user_input,
        chat_history=chat_history,
    )

    llm = get_model_provider(config).get_llm_for_node("process_context")
    response = await llm.ainvoke(prompt_messages)

    try:
        parser = JsonOutputParser()
        parsed_response = parser.parse(str(response.content))

        enhanced_query = parsed_response.get("enhanced_query", user_input)
        context_summary = parsed_response.get("context_summary", "")
        is_follow_up = parsed_response.get("is_follow_up", False)
        need_semantic_search = parsed_response.get(
            "need_semantic_search", True
        )
        required_dataset_ids = parsed_response.get("required_dataset_ids", [])
        visualization_data = parsed_response.get("visualization_data", [])

        if context_summary and context_summary.strip():
            final_query = f"""
The original user query and the previous conversation history were processed
and the following context summary was added to the query:

{is_follow_up and "This is a follow-up question to a previous query." or ""}

User Query: {enhanced_query}

Context Summary: {context_summary}
"""
        else:
            final_query = enhanced_query

        return {
            "user_query": final_query,
            "need_semantic_search": need_semantic_search,
            "required_dataset_ids": required_dataset_ids,
            "visualization_data": visualization_data,
        }

    except Exception as e:
        logger.error(f"Error processing context: {e!s}")
        return {"user_query": user_input}
