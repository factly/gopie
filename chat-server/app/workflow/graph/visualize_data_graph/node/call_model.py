from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig

from app.tool_utils.tool_node import has_tool_calls
from app.tool_utils.tools import ToolNames
from app.utils.model_registry.model_provider import get_model_provider

from ...visualize_data_graph.types import State

tool_names = [ToolNames.RUN_PYTHON_CODE, ToolNames.RESULT_PATHS]


async def call_model(state: State, config: RunnableConfig) -> dict:
    """
    Invokes the language model for the "visualize_data" node using the current message history.
    """
    llm = get_model_provider(config).get_llm_for_node("visualize_data", tool_names)
    response = await llm.ainvoke(state["messages"])
    return {"messages": [response]}


def should_continue(state: State):
    """
    Determines the next workflow step based on the last AI message and its tool calls.

    Returns:
        str: "process_result" if result_paths tool is called, otherwise "continue" to tools.
    """
    last_message = state["messages"][-1]

    if not isinstance(last_message, AIMessage):
        return "continue"

    is_final_result = (
        len(last_message.tool_calls) == 1 and last_message.tool_calls[0]["name"] == "result_paths"
    )

    if has_tool_calls(last_message) and is_final_result:
        return "process_result"
    else:
        return "continue"
