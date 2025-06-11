import json

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from langchain_core.runnables import RunnableConfig

from app.core.log import logger
from app.utils.model_registry.model_provider import (
    get_chat_history,
    get_llm_for_node,
)
from app.workflow.graph.visualize_data_graph.types import State


class DataFormatter:
    def format_data_for_visualization(
        self, state: State, config: RunnableConfig
    ) -> dict:
        visualization_type = state.get("visualization_type")
        visualization_data = state.get("visualization_data")
        user_query = state.get("user_query")

        if not visualization_type:
            return {"formatted_data_for_visualization": None}

        try:
            # Use LLM to convert data to plotly-compatible format
            plotly_data = self._convert_data_with_llm(
                visualization_data, visualization_type, user_query, config
            )

            fig: go.Figure | None = None

            if visualization_type == "scatter":
                fig = self._create_scatter_chart(plotly_data)
            elif visualization_type in ["bar", "horizontal_bar"]:
                fig = self._create_bar_chart(plotly_data)

            if fig:
                dict_fig = fig.to_dict()
                return {"formatted_data_for_visualization": dict_fig}
            else:
                return {"error": "Failed to create chart"}
        except Exception as e:
            logger.error(f"Error formatting {visualization_type} data: {e}")
            return {"error": str(e)}

    def _convert_data_with_llm(
        self, results, visualization_type, question, config
    ):
        """Use LLM to convert data to plotly-compatible format."""
        prompt = f"""
You are a data formatting expert. Convert the given data to a
plotly-compatible format for a {visualization_type} chart.

Raw Data: {results}
Chart Type: {visualization_type}
Question: {question}

Instructions:
1. Analyze the data structure and determine the best way to format it
2. For bar/line charts: Create list of dictionaries with column names
3. For scatter plots: Ensure x, y coordinates are properly formatted
4. For pie charts: Ensure you have 'names' and 'values' columns
5. Handle multi-series data appropriately

Return ONLY a JSON object in this format:
{{
    "data": [list of dictionaries representing rows],
    "columns": ["column1", "column2", ...],
    "chart_type_specific_info": {{
        "x_column": "name of x column",
        "y_column": "name of y column",
        "color_column": "name of color/series column (if applicable)",
        "names_column": "name of names column (for pie charts)",
        "values_column": "name of values column (for pie charts)"
    }}
}}

Examples:
For 2-column data:
{{"data": [{{"category": "A", "value": 10}}, {{"category": "B", "value": 20}}],
"columns": ["category", "value"],
"chart_type_specific_info": {{"x_column": "category", "y_column": "value"}}}}

For 3-column data:
{{"data": [{{"x": "Jan", "series": "Sales", "y": 100}},
{{"x": "Jan", "series": "Profit", "y": 50}}],
"columns": ["x", "series", "y"],
"chart_type_specific_info": {{"x_column": "x", "y_column": "y",
"color_column": "series"}}}}
"""

        llm = get_llm_for_node("format_data_for_visualization", config)
        response = llm.invoke(
            {"input": prompt, "chat_history": get_chat_history(config)}
        )

        try:
            converted_data = json.loads(str(response.content).strip())
            df = pd.DataFrame(converted_data["data"])
            return {
                "dataframe": df,
                "info": converted_data["chart_type_specific_info"],
            }
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"LLM data conversion failed: {e}, using fallback")

    def _create_scatter_chart(self, plotly_data):
        df = plotly_data["dataframe"]
        info = plotly_data["info"]
        x_col = info.get("x_column")
        y_col = info.get("y_column")
        color_col = info.get("color_column")
        fig = px.scatter(df, x=x_col, y=y_col, color=color_col)

        return fig

    def _create_bar_chart(self, plotly_data):
        df = plotly_data["dataframe"]
        info = plotly_data["info"]
        x_col = info.get("x_column")
        y_col = info.get("y_column")
        color_col = info.get("color_column")
        fig = px.bar(df, x=x_col, y=y_col, color=color_col)
        return fig
