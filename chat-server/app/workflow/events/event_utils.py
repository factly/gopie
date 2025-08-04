from functools import wraps
from typing import Any

from langchain_core.runnables import RunnableConfig

from app.models.chat import NodeEventConfig, Role


def configure_node(
    role: str,
    progress_message: str = "Processing...",
):
    def decorator(func):
        @wraps(func)
        async def wrapper(state: Any, config: RunnableConfig, *args, **kwargs):
            metadata = NodeEventConfig(
                role=Role(role),
                progress_message=progress_message,
            )

            config.update(metadata=metadata.model_dump())

            return await func(state, config, *args, **kwargs)

        return wrapper

    return decorator
