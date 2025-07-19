from app.tool_utils.tools import ToolNames
from ...visualize_data_graph.types import State
from langchain_core.runnables import RunnableConfig
from app.utils.model_registry.model_provider import get_model_provider
from langchain_core.messages import AIMessage

tool_names = [ToolNames.RUN_PYTHON_CODE, ToolNames.RESULT_PATHS]

async def call_model(state: State, config: RunnableConfig) -> dict:
    """
    Invokes the language model for the "visualize_data" node using the current message history.

    Returns:
        dict: A dictionary containing the model's response message under the "messages" key.
    """
    llm = get_model_provider(config).get_llm_for_node("visualize_data", tool_names)
    response = await llm.ainvoke(state["messages"])
    return {"messages": [response]}


def should_continue(state: State):
    """
    Determines the next workflow step based on the last AI message and its tool calls.

    Returns:
        str: "respond" if the last AI message contains exactly one tool call named "result_paths"; otherwise, "continue".
    """
    last_message = state["messages"][-1]
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        if len(last_message.tool_calls) == 1 and last_message.tool_calls[0]["name"] == "result_paths":
            return "process_result"
    return "continue"