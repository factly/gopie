from langchain_core.language_models.fake_chat_models import (
    GenericFakeChatModel,
)
from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig

from app.workflow.events.event_utils import configure_node

from ...visualize_data_graph.types import State


@configure_node(
    role="ai",
    progress_message="",
)
async def respond(state: State, config: RunnableConfig) -> dict:
    result = state["result"]
    if result.data:
        response_content = "Visualization generated successfully and can be found in the result tab"
    else:
        response_content = (
            "Visualization failed to generate, please try again by rephrasing your query"
        )
    response_message = AIMessage(content=response_content)
    llm = GenericFakeChatModel(
        messages=iter([response_message]), metadata=config.get("metadata", {})
    )
    response = await llm.ainvoke(response_message.content)
    return {"messages": [response]}
