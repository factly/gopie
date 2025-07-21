from typing import Annotated

from langgraph.types import Command
from e2b_code_interpreter import AsyncSandbox
from langchain_core.messages import ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool, InjectedToolCallId
from langgraph.prebuilt import InjectedState


@tool
async def run_python_code(
    code: str,
    sandbox: Annotated[AsyncSandbox, InjectedState("sandbox")],
    tool_call_id: Annotated[str, InjectedToolCallId],
    config: RunnableConfig,
):
    """Run python code in a sandbox.
    Pandas and Altair are already installed.
    The dataset csv are saved in the `csv_path` locations.
    Always use altair to create visualizations and save them to json.
    To get any output in the logs, use the print function.

    Return the logs and error if any.
    """
    execution = await sandbox.run_code(code)
    state_update = {
        "executed_python_code": code,
        "messages": [
            ToolMessage(
                tool_call_id=tool_call_id,
                content=str(
                    {
                        "logs": execution.logs,
                        "error": execution.error,
                    }
                ),
            )
        ],
    }

    return Command(
        update=state_update,
    )


def get_dynamic_tool_text(args: dict) -> str:
    return "Running python code for visualization"


__tool__ = run_python_code
__tool_category__ = "Data Visualization"
__should_display_tool__ = True
__get_dynamic_tool_text__ = get_dynamic_tool_text
