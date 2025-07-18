from typing import Literal

from langchain_core.messages import ToolCall, ToolMessage, AIMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.runnables.config import merge_configs
from langgraph.prebuilt import ToolNode

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

    def get_tool_config(self, call: ToolCall) -> RunnableConfig:
        tool_name = call.get("name")
        tool_args = call.get("args")
        metadata = self.tool_metadatas.get(tool_name, {})
        tool_text = f"Using {tool_name}"
        get_dynamic_tool_text = metadata.get("get_dynamic_tool_text", None)
        if get_dynamic_tool_text and callable(get_dynamic_tool_text):
            tool_text = get_dynamic_tool_text(tool_args)
        tool_category = metadata.get("tool_category", tool_name)
        return RunnableConfig(
            tags=["chain_tool", "display"],
            metadata={
                "tool_text": tool_text,
                "tool_category": tool_category,
            },
        )

    def _run_one(
        self,
        call: ToolCall,
        input_type: Literal["list", "dict", "tool_calls"],
        config: RunnableConfig,
    ) -> ToolMessage:
        tool_config = self.get_tool_config(call)
        return super()._run_one(call, input_type, merge_configs(config, tool_config))

    async def _arun_one(
        self,
        call: ToolCall,
        input_type: Literal["list", "dict", "tool_calls"],
        config: RunnableConfig,
    ) -> ToolMessage:
        tool_config = self.get_tool_config(call)
        return await super()._arun_one(call, input_type, merge_configs(config, tool_config))


def has_tool_calls(message):
    if isinstance(message, AIMessage) and hasattr(message, "tool_calls") and message.tool_calls:
        return True
    return False
