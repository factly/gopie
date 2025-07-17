from langchain_core.callbacks import adispatch_custom_event
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, StateGraph

from app.core.constants import VISUALIZATION_RESULT
from app.models.schema import ConfigSchema
from app.tool_utils.tool_node import ModifiedToolNode as ToolNode
from app.tool_utils.tools import ToolNames
from app.utils.langsmith.prompt_manager import get_prompt
from app.utils.model_registry.model_provider import get_model_provider
from app.models.message import ErrorMessage

from .types import AgentState, InputState, OutputState
from .utils import (
    get_sandbox,
    get_visualization_result_data,
    update_sandbox_timeout,
    upload_csv_files,
    upload_visualization_result_data,
)


async def pre_model_hook(state: AgentState, config: RunnableConfig):
    messages = []
    output = {}
    existing_sandbox = state.get("sandbox")
    try:
        if existing_sandbox:
            await update_sandbox_timeout(existing_sandbox)
        else:
            sbx = await get_sandbox()
            output["sandbox"] = sbx
            csv_paths = await upload_csv_files(sbx, state["datasets"])
        if not state.get("is_input_prepared"):
            await adispatch_custom_event("gopie-agent", {"content": "Preparing visualization ..."})

            messages = get_prompt(
                "visualize_data",
                user_query=state["user_query"],
                datasets=state["datasets"],
                csv_paths=csv_paths,
            )

            output["is_input_prepared"] = True
        output["messages"] = messages
        return output
    except ValueError as e:
        return {"messages": [ErrorMessage(content=str(e))]}


tool_names = [ToolNames.RUN_PYTHON_CODE, ToolNames.RESULT_PATHS]


async def call_model(state: AgentState, config: RunnableConfig):
    llm = get_model_provider(config).get_llm_for_node("visualize_data", tool_names)
    response = await llm.ainvoke(state["messages"])
    return {"messages": [response]}


async def respond(state: AgentState):
    tool_call = state["messages"][-1].tool_calls[0]
    response = tool_call["args"]
    visualization_result_data = await get_visualization_result_data(
        state["sandbox"], response["visualization_result_paths"]
    )
    s3_paths = await upload_visualization_result_data(visualization_result_data)
    tool_message = {
        "type": "tool",
        "content": "Here is your visualization result",
        "tool_call_id": tool_call["id"],
    }
    await state["sandbox"].kill()

    await adispatch_custom_event(
        "gopie-agent",
        {
            "content": "Visualization Created",
            "name": VISUALIZATION_RESULT,
            "values": {"s3_paths": s3_paths},
        },
    )
    return {"messages": [tool_message], "s3_paths": s3_paths}


def should_continue(state: AgentState):
    messages = state["messages"]
    last_message = messages[-1]
    if len(last_message.tool_calls) == 1 and last_message.tool_calls[0]["name"] == "result_paths":
        return "respond"
    else:
        return "continue"


workflow = StateGraph(
    state_schema=AgentState,
    config_schema=ConfigSchema,
    input=InputState,
    output=OutputState,
)
workflow.add_node("agent", call_model)
workflow.add_node("pre_model_hook", pre_model_hook)
workflow.add_node("respond", respond)
workflow.add_node("tools", ToolNode(tool_names))

workflow.set_entry_point("pre_model_hook")

workflow.add_conditional_edges(
    "agent",
    should_continue,
    {
        "continue": "tools",
        "respond": "respond",
    },
)

workflow.add_edge("tools", "pre_model_hook")
workflow.add_edge("pre_model_hook", "agent")
workflow.add_edge("respond", END)
graph = workflow.compile()
