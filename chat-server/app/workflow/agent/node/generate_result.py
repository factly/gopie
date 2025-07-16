from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig

from app.utils.langsmith.prompt_manager import get_prompt
from app.utils.model_registry.model_provider import get_model_provider
from app.workflow.events.event_utils import configure_node
from app.workflow.agent.types import AgentState


@configure_node(
    role="ai",
    progress_message="",
)
async def generate_result(state: AgentState, config: RunnableConfig) -> dict:
    """
    Generate a response based on the query result
    """

    query_result = state["query_result"]

    llm = get_model_provider(config).get_llm_for_node("generate_result")
    prompt = get_prompt("generate_result", query_result=query_result)

    response = await llm.ainvoke(prompt)

    return {
        "messages": [AIMessage(content=str(response.content))],
    }
