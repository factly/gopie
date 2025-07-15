from app.core.log import logger
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from app.workflow.events.event_utils import configure_node

from ..types import AgentState


@configure_node(
    role="ai",
    progress_message="",
)
async def stream_invalid_response(state: AgentState, config: RunnableConfig):
    last_message = state.get("messages", [])[-1]
    if not isinstance(last_message, AIMessage):
        logger.debug(f"Last message is not an AIMessage: {last_message}")
        pass

    llm = GenericFakeChatModel(messages=iter([last_message]), metadata=config.get("metadata", {}))
    response = await llm.ainvoke(input=last_message.content)

    return {
        "messages": [AIMessage(content=response.content)],
    }
