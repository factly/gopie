import orjson
from langchain_core.callbacks import adispatch_custom_event
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.runnables import RunnableConfig

from app.core.constants import VISUALIZATION_RESULT, VISUALIZATION_RESULT_ARG
from app.models.message import ErrorMessage
from app.workflow.events.event_utils import configure_node
from app.workflow.graph.visualize_data_graph.utils import (
    add_context_to_python_code,
    get_visualization_result_bytes,
    get_visualization_result_data,
    upload_visualization_result_data,
)

from ..types import State


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
    datasets = state["datasets"]

    try:
        if isinstance(last_message, ErrorMessage):
            raise ValueError(last_message.content)

        if not isinstance(last_message, AIMessage) or not last_message.tool_calls:
            raise ValueError("No tool calls found in the last message")

        tool_call = last_message.tool_calls[0]
        response = tool_call["args"]
        sandbox = state.get("sandbox")
        result_path = response["visualization_result_paths"]
        executed_python_code = state["executed_python_code"]

        result_data = await get_visualization_result_data(sandbox=sandbox, file_names=result_path)
        final_result_data = []
        for result in result_data:
            result = orjson.loads(result)
            # removing the default config
            result.pop("config")
            # set the width and height to responsive
            result["width"] = "container"
            result["height"] = "container"
            # convert the result to string
            result = orjson.dumps(result)
            final_result_data.append(result)
        python_code_with_context = await add_context_to_python_code(
            python_code=executed_python_code, datasets=datasets
        )
        s3_paths = await upload_visualization_result_data(
            data=final_result_data, python_code=python_code_with_context
        )

        visualization_results.data = final_result_data

        # Additionally, try to fetch PNG counterparts for brief image-based summary in respond node
        png_images_b64: list[str] = []
        try:
            png_file_names = [
                p.rsplit("-", 1)[0].strip().replace(".json", ".png") for p in result_path
            ]
            png_bytes_list = await get_visualization_result_bytes(
                sandbox=sandbox, file_names=png_file_names
            )
            import base64

            for img in png_bytes_list:
                if isinstance(img, (bytes, bytearray)):
                    png_images_b64.append(base64.b64encode(img).decode("utf-8"))
        except Exception:
            png_images_b64 = []

        await adispatch_custom_event(
            "gopie-agent",
            {
                "content": "Visualization Created",
                "name": VISUALIZATION_RESULT,
                "values": {VISUALIZATION_RESULT_ARG: s3_paths},
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
            "s3_paths": s3_paths,
            "result_images_b64": png_images_b64,
        }

    except Exception as e:
        error_msg = f"Error processing visualization result: {str(e)}"
        visualization_results.errors.append(f"[ERROR] {error_msg}")

        return {
            "messages": [ErrorMessage(content=error_msg)],
            "result": visualization_results,
            "s3_paths": [],
            "result_images_b64": [],
        }
