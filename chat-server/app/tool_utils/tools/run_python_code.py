import re
from typing import Annotated

from e2b_code_interpreter import AsyncSandbox
from langchain_core.messages import ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolCallId, tool
from langgraph.prebuilt import InjectedState
from langgraph.types import Command


def extract_viz_name_from_code(code: str) -> str:
    viz_name = set()
    save_patterns = re.findall(r"\.save\(['\"]([^'\"]+)\.(?:json|png)['\"]\)", code)
    for pattern in save_patterns:
        viz_name.add(pattern)
    return list(viz_name)[0] if viz_name else "visualization"


@tool
async def run_python_code(
    code: str,
    sandbox: Annotated[AsyncSandbox, InjectedState("sandbox")],
    tool_call_id: Annotated[str, InjectedToolCallId],
    config: RunnableConfig,
    status_message: str = "",
):
    """
    Execute Python code to create data visualizations.

    Generate ONE visualization at a time. Use descriptive names (e.g., 'revenue_trend', not 'viz1').
    Save both .json and .png with the same name.

    Example:
    ```python
    import pandas as pd
    import altair as alt

    df = pd.read_csv('result_0.csv')
    chart = alt.Chart(df).mark_bar().encode(x='category:N', y='sales:Q')

    chart.save('sales_by_category.json')
    chart.save('sales_by_category.png')
    ```

    Pandas and Altair are pre-installed. CSV files are at the paths provided in the prompt.
    """
    execution = await sandbox.run_code(code)
    code_dict = {extract_viz_name_from_code(code): code}

    state_update = {
        "executed_python_code": code_dict,
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
    return args.get("status_message") or "Getting your visualization ready"


__tool__ = run_python_code
__tool_category__ = "Data Visualization"
__should_display_tool__ = True
__get_dynamic_tool_text__ = get_dynamic_tool_text
