from typing import Literal, Union

from langchain_core.messages import AIMessage, ToolCall, ToolMessage
from langchain_core.runnables.config import RunnableConfig, merge_configs
from langgraph.prebuilt import ToolNode
from langgraph.types import Command

from app.tool_utils.tools import ToolNames

from .tools import get_tools


class ModifiedToolNode(ToolNode):
    def __init__(
        self,
        tool_names: list[ToolNames],
        *args,
        **kwargs,
    ) -> None:
        tools = get_tools(tool_names)
        tool_functions = [tool for tool, _ in tools.values()]
        tool_metadatas = {tool_name: tool_data[1] for tool_name, tool_data in tools.items()}
        self.tool_metadatas = tool_metadatas
        super().__init__(*args, tools=tool_functions, **kwargs)

    def _apply_tool_metadata(self, call: ToolCall, config: RunnableConfig) -> RunnableConfig:
        tool_name = call.get("name")
        tool_args = call.get("args")
        metadata = self.tool_metadatas.get(tool_name, {})

        tool_text = f"Using {tool_name}"
        get_dynamic_tool_text = metadata.get("get_dynamic_tool_text", None)

        if get_dynamic_tool_text and callable(get_dynamic_tool_text):
            tool_text = get_dynamic_tool_text(tool_args)
        tool_category = metadata.get("tool_category", tool_name)
        should_display_tool = metadata.get("should_display_tool", False)

        tool_config: RunnableConfig = {
            "tags": ["chain_tool", "display"],
            "metadata": {
                "tool_text": tool_text,
                "tool_category": tool_category,
                "should_display_tool": should_display_tool,
            },
        }

        return merge_configs(config, tool_config)

    def _run_one(
        self,
        call: ToolCall,
        input_type: Literal["list", "dict", "tool_calls"],
        config: RunnableConfig,
    ) -> Union[ToolMessage, Command]:
        updated_config = self._apply_tool_metadata(call, config)
        return super()._run_one(call, input_type, updated_config)

    async def _arun_one(
        self,
        call: ToolCall,
        input_type: Literal["list", "dict", "tool_calls"],
        config: RunnableConfig,
    ) -> Union[ToolMessage, Command]:
        updated_config = self._apply_tool_metadata(call, config)
        return await super()._arun_one(call, input_type, updated_config)


def has_tool_calls(message):
    """
    Determine whether the given message is an AIMessage instance with non-empty tool calls.

    Returns:
        bool: True if the message is an AIMessage and its 'tool_calls' attribute is non-empty; otherwise, False.
    """
    if isinstance(message, AIMessage) and hasattr(message, "tool_calls") and message.tool_calls:
        return True
    return False
