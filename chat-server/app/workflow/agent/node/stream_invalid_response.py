from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig

from app.utils.model_registry.model_provider import get_model_provider
from app.workflow.events.event_utils import configure_node

from ..types import AgentState


@configure_node(
    role="ai",
    progress_message="",
)
async def stream_invalid_response(state: AgentState, config: RunnableConfig):
    last_message = state.get("messages", [])[-1].content

    prompt = [
        HumanMessage(
            content=f"Please output exactly this message, word for word, "
            f"with no additions or modifications: {last_message}"
        )
    ]

    llm = get_model_provider(config).get_llm("gpt-3.5-turbo")
    response = await llm.ainvoke(prompt)

    return {
        "messages": [AIMessage(content=response.content)],
    }
