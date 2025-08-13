import json
from functools import wraps
from typing import Any

from langchain_core.callbacks import adispatch_custom_event
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from app.core.log import logger
from app.models.chat import NodeEventConfig, Role
from app.utils.model_registry.model_provider import get_llm_for_other_task


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


async def create_dynamic_progress_message(context: str, config: RunnableConfig) -> str:
    """
    Create a dynamic progress message based on the messages.
    """
    llm = get_llm_for_other_task("progress_message", config)

    messages = [
        SystemMessage(
            content="""
You are a status announcer for a developer tool, similar to Cursor IDE.
Your job is to turn the given technical status into a short, friendly, natural-sounding progress update.

Rules:
- Keep it casual, conversational, and in-the-moment, like a real-time IDE status message.
- Be concise: maximum 100 characters.
- Avoid technical jargon unless it's extremely common for developers.
- Match the flow of what's currently happening in the context.
- Do NOT include quotes or formatting, just output the plain string.
- Make it feel like it's coming from a helpful assistant quietly updating the user.
"""
        ),
        HumanMessage(
            content=json.dumps(
                {
                    "context": context,
                }
            )
        ),
    ]

    response = await llm.ainvoke(messages)
    progress_message = str(response.content)

    return progress_message


async def stream_dynamic_message(context: str, config: RunnableConfig):
    """
    Stream a dynamic message based on the context.
    """
    config.update(
        metadata=NodeEventConfig(
            role=Role.AI,
            progress_message="",
        ).model_dump()
    )

    dynamic_message = await create_dynamic_progress_message(context, config)

    logger.debug(dynamic_message)

    config.update(
        metadata=NodeEventConfig(
            role=Role.INTERMEDIATE,
            progress_message="",
        ).model_dump()
    )

    return dynamic_message


async def non_streaming_dynamic_message(context: str, config: RunnableConfig):
    """
    Send a non-streaming dynamic message based on the context.
    """
    dynamic_message = await create_dynamic_progress_message(context, config)

    await adispatch_custom_event(
        "gopie-agent",
        {
            "content": dynamic_message,
        },
    )
