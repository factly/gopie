import json

from langchain_core.messages import ToolMessage


class ToolNode:
    """A node that runs the tools requested in the last AIMessage and returns to the calling node"""

    def __init__(self, tools: list) -> None:
        self.tools = {tool.name: tool for tool in tools}

    async def __call__(self, state: dict):
        if messages := state.get("messages", []):
            message = messages[-1]
        else:
            raise ValueError("No message found in input")

        outputs = []
        all_tool_results = []

        for tool_call in message.tool_calls:
            tool_result = await self.tools[tool_call["name"]].ainvoke(tool_call["args"])

            all_tool_results.append({"tool": tool_call["name"], "result": tool_result})

            outputs.append(
                ToolMessage(
                    content=json.dumps(tool_result),
                    name=tool_call["name"],
                    tool_call_id=tool_call["id"],
                )
            )

        query_result = state.get("query_result", [])
        query_index = state.get("subquery_index", -1)
        query_result.subqueries[query_index].tool_used_result = all_tool_results

        return {
            "query_result": query_result,
            "messages": outputs,
        }


def has_tool_calls(message):
    """Helper function to check if a message has tool calls"""
    if hasattr(message, "tool_calls") and message.tool_calls:
        return True

    if (
        hasattr(message, "additional_kwargs")
        and "tool_calls" in message.additional_kwargs
    ):
        return True

    return False
