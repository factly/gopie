from langchain_core.callbacks import adispatch_custom_event
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from app.models.schema import ConfigSchema
from app.utils.model_registry.model_provider import get_llm_for_node
from app.workflow.events.event_utils import configure_node

from .types import AgentState, InputState, OutputState, ResultPaths
from .utils import (
    get_sandbox,
    get_visualization_result_data,
    run_python_code,
    update_sandbox_timeout,
    upload_csv_files,
    upload_visualization_result_data,
)

# fmt: off
SYSTEM_PROMPT = """\
You are an expert data visualization engineer. Use altair to create visualizations, and save them to json.
Do not create the date, read the data from the csv_path where the data is stored.
Use the run_python_code tool to run python code.

Your task is the following:
1. Find the best way to visualize the data if the user has not specified any visualization type.
2. Use altair to create visualizations, and save them to json.
3. Use the run_python_code tool to run python code.
4. Return the paths to the json files that contain the visualizations.

First start by reasoning about the best way to visualize the data.
"""
# fmt: on


@configure_node(
    role="intermediate",
    progress_message="Preparing visualization ...",
)
async def pre_model_hook(state: AgentState, config: RunnableConfig):
    system_message = SystemMessage(content=SYSTEM_PROMPT)
    existing_sandbox = state.get("sandbox")
    if existing_sandbox:
        await update_sandbox_timeout(existing_sandbox)
    else:
        sbx = await get_sandbox()
        state["sandbox"] = sbx
        csv_paths = await upload_csv_files(sbx, state["datasets"])
    if not state.get("is_input_prepared"):
        input_data = "This is the user query: " + state["user_query"] + "\n\n"
        input_data += (
            "The following are the datasets and their descriptions: \n\n"
        )
        for idx, (dataset, csv_path) in enumerate(
            zip(state["datasets"], csv_paths)
        ):
            input_data += f"Dataset {idx + 1}: \n\n"
            input_data += f"Description: {dataset.description}\n\n"
            input_data += f"CSV Path: {csv_path}\n\n"
        state["messages"] = [HumanMessage(content=input_data)]
        state["is_input_prepared"] = True
    state["messages"] = [system_message] + state["messages"]
    return state


tools = [run_python_code, ResultPaths]


async def call_model(state: AgentState, config: RunnableConfig):
    llm = get_llm_for_node("visualize_with_code", config)
    model_with_response_tool = llm.bind_tools(tools)
    response = await model_with_response_tool.ainvoke(state["messages"])
    return {"messages": [response]}


async def respond(state: AgentState):
    tool_call = state["messages"][-1].tool_calls[0]
    response = ResultPaths(**tool_call["args"])
    visualization_result_data = await get_visualization_result_data(
        state["sandbox"], response.visualization_result_paths
    )
    s3_paths = await upload_visualization_result_data(
        visualization_result_data
    )
    tool_message = {
        "type": "tool",
        "content": "Here is your visualization result",
        "tool_call_id": tool_call["id"],
    }
    await state["sandbox"].kill()
    data_name = "visualization_result"
    data_args = {"s3_paths": s3_paths}
    await adispatch_custom_event(
        "gopie-agent",
        {
            "content": "Visualization Created",
            "name": data_name,
            "values": data_args,
        },
    )
    return {"messages": [tool_message], "s3_paths": s3_paths}


def should_continue(state: AgentState):
    messages = state["messages"]
    last_message = messages[-1]
    if (
        len(last_message.tool_calls) == 1
        and last_message.tool_calls[0]["name"] == "ResultPaths"
    ):
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
workflow.add_node("tools", ToolNode(tools))

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
