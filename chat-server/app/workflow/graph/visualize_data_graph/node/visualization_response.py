from app.workflow.events.event_utils import configure_node
from ...visualize_data_graph.types import AgentState
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import AIMessage
from app.workflow.graph.visualize_data_graph.utils import (
    get_visualization_result_data,
    upload_visualization_result_data,
)
from langchain_core.callbacks import adispatch_custom_event
from app.core.constants import VISUALIZATION_RESULT

@configure_node(
    role="ai",
    progress_message="",
)
async def respond(state: AgentState, config: RunnableConfig) -> dict:
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


