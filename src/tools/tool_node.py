import json
from langchain_core.messages import ToolMessage

class ToolNode:
  """A node that runs the tools requested in the last AIMessage and returns to the calling node"""

  def __init__(self, tools: list) -> None:
    self.tools = {tool.name: tool for tool in tools}

  def __call__(self, state: dict):
    if messages := state.get("messages", []):
        message = messages[-1]
    else:
        raise ValueError("No message found in input")

    outputs = []
    all_tool_results = state.get("tool_results", [])

    for tool_call in message.tool_calls:
        tool_result = self.tools[tool_call["name"]].invoke(
            tool_call["args"]
        )

        all_tool_results.append(
            {
                "tool": tool_call["name"],
                "result": tool_result
            }
        )

        outputs.append(
            ToolMessage(
                content=json.dumps(tool_result),
                name=tool_call["name"],
                tool_call_id=tool_call["id"],
            )
        )

    return {
       'tool_results': all_tool_results,
       "messages": outputs,
    }

def has_tool_calls(message):
    """Helper function to check if a message has tool calls"""
    if hasattr(message, 'tool_calls') and message.tool_calls:
        return True

    if hasattr(message, 'additional_kwargs') and 'tool_calls' in message.additional_kwargs:
        return True

    return False
