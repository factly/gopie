from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig

from app.utils.langsmith.prompt_manager import get_prompt_llm_chain
from app.workflow.agent.types import AgentState
from app.workflow.events.event_utils import configure_node


@configure_node(
    role="ai",
    progress_message="",
)
async def generate_result(state: AgentState, config: RunnableConfig) -> dict:
    """
    Asynchronously generates an AI response based on the provided query result.

    The function retrieves the query result from the agent state, constructs a prompt, and invokes a
    language model to generate a response. The result is returned as a dictionary containing a list
    with a single AI message.
    """

    continue_execution = state.get("continue_execution")
    if continue_execution is False:
        message_provided_stream_update = (
            "I need more specific information to provide a comprehensive answer. "
            "Could you please clarify your question or provide additional context?"
        )
        return {
            "messages": [AIMessage(content=message_provided_stream_update)],
        }

    query_result = state["query_result"]

    chain = get_prompt_llm_chain("generate_result", config)
    response = await chain.ainvoke({"query_result": query_result})

    return {
        "messages": [AIMessage(content=str(response.content))],
    }
