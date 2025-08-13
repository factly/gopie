from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig

from app.tool_utils.tool_node import has_tool_calls
from app.tool_utils.tools import ToolNames
from app.utils.model_registry.model_provider import get_configured_llm_for_node
from langgraph.types import Command
from ...visualize_data_graph.types import State

tool_names = [ToolNames.RUN_PYTHON_CODE, ToolNames.RESULT_PATHS, ToolNames.GET_FEEDBACK_FOR_IMAGE]


async def call_model(state: State, config: RunnableConfig) -> dict:
    """
    Invokes the language model for the "visualize_data" node using the current message history.
    """
    llm = get_configured_llm_for_node("visualize_data", config, tool_names=tool_names, force_tool_calls=True)
    response = await llm.ainvoke(state["messages"], parallel_tool_calls=False)
    return {"messages": [response]}


def should_continue(state: State):
    """
    Determines the next workflow step based on the last AI message and its tool calls.
    """
    last_message = state["messages"][-1]

    if isinstance(last_message, AIMessage):
        if has_tool_calls(last_message):
            is_final_result = (len(last_message.tool_calls) == 1 and last_message.tool_calls[0]["name"] == "result_paths")
            if is_final_result:
                return Command(
                    goto="process_result",
                )
            return Command(
                goto="tools",
            )
        else:
            state_update = {
                "messages": state["messages"] + [HumanMessage(content="Continue")]
            }
            return Command(
                goto="agent",
            update=state_update)
    return Command(
            goto="tools",
        )
