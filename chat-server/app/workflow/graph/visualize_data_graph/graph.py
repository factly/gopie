from langchain_core.callbacks import adispatch_custom_event
from langchain_core.messages import AIMessage
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
    """
    Prepares the environment and prompt messages for the data visualization agent before invoking the language model.

    If a sandbox already exists, its timeout is updated; otherwise, a new sandbox is created and CSV files from the datasets are uploaded. If input preparation has not yet occurred, a custom event is dispatched, prompt messages are generated using the user query and datasets, and the input is marked as prepared. Returns an updated state dictionary containing prompt messages and sandbox information. If a `ValueError` occurs, returns an error message.
    """
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
    """
    Invokes the language model for the "visualize_data" node using the current message history.

    Returns:
        dict: A dictionary containing the model's response message under the "messages" key.
    """
    llm = get_model_provider(config).get_llm_for_node("visualize_data", tool_names)
    response = await llm.ainvoke(state["messages"])
    return {"messages": [response]}


async def respond(state: AgentState):
    """
    Processes the AI tool call to retrieve, upload, and return visualization results.

    Raises:
        ValueError: If the last message is not an AIMessage with tool calls.

    Returns:
        dict: Contains a tool message indicating visualization completion and the S3 paths of the uploaded results.
    """
    last_message = state["messages"][-1]
    if not isinstance(last_message, AIMessage) or not last_message.tool_calls:
        raise ValueError("No tool calls found in the last message")

    tool_call = last_message.tool_calls[0]
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

    sandbox = state.get("sandbox")
    if sandbox is not None:
        await sandbox.kill()

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
    """
    Determines the next workflow step based on the last AI message and its tool calls.

    Returns:
        str: "respond" if the last AI message contains exactly one tool call named "result_paths"; otherwise, "continue".
    """
    last_message = state["messages"][-1]
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        if len(last_message.tool_calls) == 1 and last_message.tool_calls[0]["name"] == "result_paths":
            return "respond"
    return "continue"


workflow = StateGraph(
    state_schema=AgentState,
    config_schema=ConfigSchema,
    input_schema=InputState,
    output_schema=OutputState,
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
