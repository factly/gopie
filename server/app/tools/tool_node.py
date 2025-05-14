from langchain_core.messages import ToolMessage


class ToolNode:
    """
    A node that runs the tools requested in the last AIMessage and
    returns to the calling node
    """

    def __init__(
        self,
        tools: dict,
        tool_metadata: dict[str, dict[str, str]] | None = None,
    ) -> None:
        self.tools = tools
        self.tool_metadata = tool_metadata or {}

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

                if tool_name not in self.tools:
                    error_message = f"Tool '{tool_name}' not found"
                    all_tool_results.append(
                        {
                            "tool": tool_name,
                            "error": error_message,
                        }
                    )
                    continue

                tool = self.tools[tool_name]

                metadata = self.tool_metadata.get(tool_name, {})

                tool_text = f"Using {tool_name}"
                get_dynamic_tool_text = metadata.get(
                    "get_dynamic_tool_text", None
                )
                if get_dynamic_tool_text and callable(get_dynamic_tool_text):
                    tool_text = get_dynamic_tool_text(tool_args)

                tool_category = metadata.get("tool_category", tool_name)

                tool_config = {
                    "tags": ["chain_tool", "display"],
                    "metadata": {
                        "tool_text": tool_text,
                        "tool_category": tool_category,
                    },
                }

                tool_result = None
                async for event in tool.astream_events(
                    tool_args, config=tool_config
                ):
                    if event["event"] == "on_tool_end":
                        tool_result = event["data"]["output"]

                all_tool_results.append(
                    {"tool": tool_name, "result": tool_result}
                )

                if tool_result is None:
                    tool_result = "No result from tool"

                outputs.append(
                    ToolMessage(
                        content=tool_result,
                        name=tool_name,
                        tool_call_id=tool_call["id"],
                    )
                )
            except Exception as e:
                error_message = f"Error executing tool: {str(e)}"
                all_tool_results.append(
                    {
                        "tool": tool_name,
                        "error": error_message,
                    }
                )

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
    return False
