from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig

from app.utils.langsmith.prompt_manager import get_prompt
from app.utils.model_registry.model_provider import (
    get_chat_history,
    get_llm_for_node,
)
from app.workflow.events.event_utils import configure_node
from app.workflow.graph.single_dataset_graph.types import State


@configure_node(
    role="ai",
    progress_message="",
)
async def response(state: State, config: RunnableConfig) -> dict:
    query_result = state.get("query_result", {})

    if not query_result:
        return {"messages": [AIMessage(content="No query result found")]}

    prompt_messages = get_prompt(
        "response",
        query_result=query_result,
    )

    llm = get_llm_for_node("response", config)
    response_result = await llm.ainvoke(
        {"input": prompt_messages, "chat_history": get_chat_history(config)}
    )
    response_text = str(response_result.content)

    return {
        "messages": [AIMessage(content=response_text)],
        "response_text": response_text,
    }
