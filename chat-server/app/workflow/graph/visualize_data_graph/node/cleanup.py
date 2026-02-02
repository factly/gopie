from langchain_core.runnables import RunnableConfig

from app.core.log import custom_logger as logger
from app.workflow.events.event_utils import configure_node

from ...visualize_data_graph.types import State


@configure_node(
    role="intermediate",
    progress_message="Cleaning up resources...",
)
async def cleanup_resources(state: State, config: RunnableConfig) -> dict[str, None]:
    """
    Centralized cleanup node that handles sandbox termination and resource cleanup.
    This ensures sandbox is always properly cleaned up regardless of how the workflow ends.
    """
    sandbox = state.get("sandbox")
    if sandbox is not None:
        try:
            await sandbox.kill()
        except Exception as e:
            logger.warning(f"Failed to cleanup sandbox: {e!s}", exc_info=True)

    return {
        "sandbox": None,
    }
