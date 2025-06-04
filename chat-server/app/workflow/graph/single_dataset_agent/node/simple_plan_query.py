from typing import Any

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig


async def simple_plan_query(state: Any, config: RunnableConfig) -> dict:
    return {"messages": [AIMessage(content="Hello, world!")]}
