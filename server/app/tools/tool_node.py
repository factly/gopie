from langchain_core.messages import ToolMessage


class ToolNode:
    """
    A node that runs the tools requested in the last AIMessage and
    returns to the calling node
    """

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
            try:
                tool_name = tool_call["name"]
                tool_args = tool_call["args"]
                tool_config = {
                    "tags": ["chain_tool", "display"],
                    "metadata": {
                        "tool_text": f"Using {tool_name}",
                        "tool_category": tool_name,
                    },
                }

                if tool_name not in self.tools:
                    error_message = f"Tool '{tool_name}' not found"
                    print(error_message)
                    continue

                tool_result = await self.tools[tool_name].ainvoke(
                    tool_args, config=tool_config
                )

                all_tool_results.append(
                    {"tool": tool_name, "result": tool_result}
                )

                outputs.append(
                    ToolMessage(
                        content=tool_result,
                        name=tool_name,
                        tool_call_id=tool_call["id"],
                    )
                )
            except Exception as e:
                error_message = f"Error executing tool: {str(e)}"
                print(error_message)

        query_result = state.get("query_result")
        query_index = state.get("subquery_index", -1)

        if query_result and query_index >= 0:
            if not query_result.subqueries[query_index].tool_used_result:
                query_result.subqueries[query_index].tool_used_result = []

            query_result.subqueries[query_index].tool_used_result.extend(
                all_tool_results
            )

        return {
            "query_result": query_result,
            "messages": outputs,
        }


def has_tool_calls(message):
    if hasattr(message, "tool_calls") and message.tool_calls:
        return True

    if (
        hasattr(message, "additional_kwargs")
        and "tool_calls" in message.additional_kwargs
    ):
        return True

    return False
