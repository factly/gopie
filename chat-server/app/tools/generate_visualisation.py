from typing import Any

import plotly.express as px
from langchain_core.tools import tool


@tool
async def generate_visualisation(
    data: list[dict],
    chart_type: str = "bar",
    x: str = "",
    y: str = "",
    title: str = "",
) -> Any:
    """
    Generate a Plotly chart from data.

    Situation to use this tool:
    - The user is asking to visualise the data that you already have either
      provided by user or user is asking to plot the data from
      previous messages.

    Args:
        data: List of dict rows.
        chart_type: 'bar', 'line', 'scatter', or 'pie'.
        x: Field for x-axis or names.
        y: Field for y-axis or values.
        title: Chart title.

    Returns:
        Dict with 'html' snippet and 'figure' JSON.
    """
    try:
        if chart_type == "bar":
            fig = px.bar(data_frame=data, x=x, y=y, title=title)
        elif chart_type == "line":
            fig = px.line(data_frame=data, x=x, y=y, title=title)
        elif chart_type == "scatter":
            fig = px.scatter(data_frame=data, x=x, y=y, title=title)
        elif chart_type == "pie":
            fig = px.pie(data_frame=data, names=x, values=y, title=title)
        else:
            raise ValueError(f"Unsupported chart_type: {chart_type}")

        html = fig.to_html(include_plotlyjs="cdn", full_html=False)
        figure_json = fig.to_dict()
        return {"html": html, "figure": figure_json}
    except Exception as e:
        return {"error": str(e)}


def get_dynamic_tool_text(args: dict) -> str:
    ct = args.get("chart_type", "")
    return f"Generating Plotly {ct or 'chart'}"


# __tool__ = generate_visualisation
# __tool_category__ = "Data Visualization"
# __get_dynamic_tool_text__ = get_dynamic_tool_text
