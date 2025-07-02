from typing import Annotated

from e2b_code_interpreter import AsyncSandbox
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState


@tool
async def run_python_code(
    code: str,
    sandbox: Annotated[AsyncSandbox, InjectedState("sandbox")],
    config: RunnableConfig,
):
    """Run python code in a jupyter notebook sandbox.
    Already has basic data visualization libraries installed.
    Always use altair to create visualizations and save them to json.
    """
    execution = await sandbox.run_code(code)
    return execution.logs


def get_dynamic_tool_text(args: dict) -> str:
    return "Running python code for visualization"


__tool__ = run_python_code
__tool_category__ = "Data Visualization"
__should_display_tool__ = True
__get_dynamic_tool_text__ = get_dynamic_tool_text
