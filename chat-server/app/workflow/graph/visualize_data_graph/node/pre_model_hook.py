from langchain_core.callbacks.manager import adispatch_custom_event
from langchain_core.runnables import RunnableConfig

from app.core.log import logger
from app.models.message import ErrorMessage
from app.utils.langsmith.prompt_manager import get_prompt
from app.workflow.events.event_utils import configure_node
from app.workflow.graph.visualize_data_graph.types import (
    State,
    VisualizationResult,
)
from app.workflow.graph.visualize_data_graph.utils import (
    format_dataset_info,
    get_python_code_files,
    get_sandbox,
    update_sandbox_timeout,
    upload_csv_files,
)


@configure_node(
    role="intermediate",
    progress_message="Preparing visualizations...",
)
async def pre_model_hook(state: State, config: RunnableConfig):
    """
    Prepares the environment and prompt messages for the data visualization agent.
    Handles tool call counting and initial setup.
    """

    result = state.get("result", VisualizationResult(data=[], errors=[]))

    try:
        existing_sandbox = state.get("sandbox")
        if existing_sandbox:
            await update_sandbox_timeout(sandbox=existing_sandbox)
            sandbox = existing_sandbox
        else:
            sandbox = await get_sandbox()
            await upload_csv_files(sandbox=sandbox, datasets=state.get("datasets", []))

        messages = []
        if not state.get("is_input_prepared"):
            await adispatch_custom_event("gopie-agent", {"content": "Preparing visualization ..."})

            datasets_csv_info = format_dataset_info(datasets=state.get("datasets", []))

            previous_python_code = ""

            if state.get("previous_visualization_json_paths"):
                previous_python_code_files = await get_python_code_files(
                    viz_paths=state["previous_visualization_json_paths"]
                )
                previous_python_code = "\n".join(previous_python_code_files)

            messages = get_prompt(
                "visualize_data",
                user_query=state["user_query"],
                datasets_csv_info=datasets_csv_info,
                previous_python_code=previous_python_code,
                feedback_count=state.get("feedback_count", 0),
                tool_call_count=state.get("tool_call_count", 0),
            )

        return {
            "messages": messages,
            "sandbox": sandbox,
            "result": result,
            "is_input_prepared": True,
            "tool_call_count": state.get("tool_call_count", 0),
        }

    except Exception as e:
        err_msg = f"Error while preparing visualizations: {str(e)}"
        result.errors.append(f"[ERROR] {err_msg}")
        logger.error(err_msg)

        return {
            "messages": [ErrorMessage(content=err_msg)],
            "result": result,
            "sandbox": state.get("sandbox"),
            "is_input_prepared": state.get("is_input_prepared", False),
            "tool_call_count": state.get("tool_call_count", 0),
        }


def should_continue_from_pre_model_hook(state: State):
    """
    Determines the next step after pre_model_hook.

    Returns:
        str: "cleanup" if there was an error, otherwise "agent".
    """
    if state.get("messages") and len(state["messages"]) > 0:
        last_message = state["messages"][-1]
        if isinstance(last_message, ErrorMessage):
            return "cleanup"
    return "agent"
