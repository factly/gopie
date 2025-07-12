from typing import Annotated

from langchain_core.messages import ToolMessage
from langchain_core.tools import BaseTool, InjectedToolCallId, tool
from langgraph.graph import MessagesState
from langgraph.prebuilt import InjectedState
from langgraph.types import Command


def create_handoff_tool(*, agent_name: str, description: str | None = None) -> BaseTool:
    name = f"transfer_to_{agent_name}"
    description = description or f"Ask {agent_name} for help."

    @tool(name, description=description)
    def handoff_tool(
        state: Annotated[MessagesState, InjectedState],
        tool_call_id: Annotated[str, InjectedToolCallId],
    ) -> Command:
        tool_message = ToolMessage(
            role="tool",
            content=f"Successfully transferred to {agent_name} agent",
            name=name,
            tool_call_id=tool_call_id,
        )

        return Command(
            goto=agent_name,
            graph=Command.PARENT,
            update={
                **state,
                "messages": state["messages"] + [tool_message],
                "active_agent": agent_name,
            },
        )

    return handoff_tool
