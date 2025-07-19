from app.models.message import ErrorMessage
from app.workflow.events.event_utils import configure_node
from ..types import State
from langchain_core.runnables import RunnableConfig
from langchain_core.messages import AIMessage
from app.workflow.graph.visualize_data_graph.utils import (
    get_visualization_result_data,
    upload_visualization_result_data,
)
from langchain_core.callbacks import adispatch_custom_event
from app.core.constants import VISUALIZATION_RESULT
from langchain_core.messages import ToolMessage

@configure_node(
    role="intermediate",
    progress_message="Processing visualization result...",
)
async def process_visualization_result(state: State, config: RunnableConfig) -> dict:
    """
    Processes the AI tool call to retrieve, upload, and return visualization results.

    Raises:
        ValueError: If the last message is not an AIMessage with tool calls.

    Returns:
        dict: Contains a tool message indicating visualization completion and the S3 paths of the uploaded results.
    """
    last_message = state["messages"][-1]
    visualization_results = state["result"]

    try:
        if not isinstance(last_message, AIMessage) or not last_message.tool_calls:
            raise ValueError("No tool calls found in the last message")

        tool_call = last_message.tool_calls[0]
        response = tool_call["args"]
        sandbox = state.get("sandbox")
        result_path = response["visualization_result_paths"]

        result_data = await get_visualization_result_data(sandbox=sandbox, file_names=result_path)
        s3_paths = await upload_visualization_result_data(data=result_data)

        visualization_results.data = result_data

        await adispatch_custom_event(
            "gopie-agent",
            {
                "content": "Visualization Created",
                "name": VISUALIZATION_RESULT,
                "values": {"s3_paths": s3_paths},
            },
        )

        return {
            "messages": [
                ToolMessage(
                    content="Here is your visualization result",
                    tool_call_id=tool_call["id"],
                )
            ],
            "result": visualization_results,
            "s3_paths": s3_paths
        }

    except Exception as e:
        error_msg = f"Error processing visualization result: {str(e)}"
        visualization_results.errors.append(f"[ERROR] {error_msg}")

        return {
            "messages": [ErrorMessage(content=error_msg)],
            "result": visualization_results,
            "s3_paths": []
        }

