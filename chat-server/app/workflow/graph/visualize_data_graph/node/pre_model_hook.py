from app.models.message import ErrorMessage
from app.utils.langsmith.prompt_manager import get_prompt
from app.workflow.events.event_utils import configure_node
from ...visualize_data_graph.types import State, VisualizationResult
from langchain_core.runnables import RunnableConfig
from langchain_core.callbacks.manager import adispatch_custom_event
from app.core.config import settings
from app.core.log import logger

from app.workflow.graph.visualize_data_graph.utils import get_sandbox, update_sandbox_timeout, upload_csv_files

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
    tool_call_count = state.get("tool_call_count", 0)
    prev_csv_paths = state["prev_csv_paths"] or []

    if tool_call_count > settings.MAX_TOOL_CALL_LIMIT:
        result.errors.append("Maximum tool call limit reached during visualization generation")
        return {
            "messages": [ErrorMessage(content="Tool call limit exceeded")],
            "result": result,
        }

    try:
        existing_sandbox = state.get("sandbox")
        if existing_sandbox:
            await update_sandbox_timeout(existing_sandbox)
            sandbox = existing_sandbox
        else:
            sandbox = await get_sandbox()
            csv_paths = await upload_csv_files(sandbox, state["datasets"])

        messages = []
        if not state.get("is_input_prepared"):
            await adispatch_custom_event("gopie-agent", {"content": "Preparing visualization ..."})

            datasets_csv_info = ""
            datasets = state["datasets"]
            for idx, (dataset, csv_path) in enumerate(zip(datasets, csv_paths)):
                datasets_csv_info += f"Dataset {idx + 1}: \n\n"
                datasets_csv_info += f"Description: {dataset.description}\n\n"
                datasets_csv_info += f"CSV Path: {csv_path}\n\n"

            for idx, csv_path in enumerate(prev_csv_paths):
                datasets_csv_info += f"Previous CSV Path {idx + 1}: {csv_path}\n\n"

            messages = get_prompt(
                "visualize_data",
                user_query=state["user_query"],
                datasets_csv_info=datasets_csv_info,
            )

        return {
            "messages": messages,
            "sandbox": sandbox,
            "result": result,
            "tool_call_count": tool_call_count,
            "is_input_prepared": True,
        }

    except Exception as e:
        err_msg = f"Error while preparing visualizations: {str(e)}"
        result.errors.append(f"[ERROR] {err_msg}")
        logger.error(err_msg)

        return {
            "messages": [ErrorMessage(content=err_msg)],
            "result": result,
            "tool_call_count": tool_call_count,
            "sandbox": state.get("sandbox"),
            "is_input_prepared": state.get("is_input_prepared", False),
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