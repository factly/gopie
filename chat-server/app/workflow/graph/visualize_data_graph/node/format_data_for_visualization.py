import json
import os

import plotly.graph_objects as go
from langchain_core.output_parsers import JsonOutputParser
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
        viz_type = state.get("viz_type")
        viz_data = state.get("viz_data")
        user_query = state.get("user_query")

        if not viz_type:
            return {"formatted_viz_data": None}

        try:
            plotly_data, reasoning = self._format_data_with_llm(
                viz_data, viz_type, user_query, config
            )

            if not plotly_data:
                return {
                    "error": "Failed to convert data for visualization",
                    "reasoning": reasoning,
                }

            fig = go.Figure(plotly_data)

            if fig:
                dict_fig = fig.to_dict()
                self._save_as_image(fig)
                return {"formatted_viz_data": dict_fig, "reasoning": reasoning}
            else:
                error_msg = f"Unsupported or failed to create {viz_type} chart"
                return {"error": error_msg, "reasoning": reasoning}
        except Exception as e:
            logger.error(f"Error formatting {viz_type} data: {e}")
            return {"error": str(e), "reasoning": str(e)}

    def _format_data_with_llm(
        self, results, viz_type, question, config
    ) -> tuple[dict, str]:
        prompt = f"""
You are a data formatting expert. Convert the given data to a
plotly-compatible format for a {viz_type} chart.

Raw Data: {results}
Chart Type: {viz_type}
Question: {question}

Return ONLY a JSON object that can be directly passed to
plotly.graph_objects.Figure. Provide the data in the Plotly_data key in the
below given JSON format.
{{
    "plotly_data" : {{}},
    "reasoning" : "reasoning for the plotly_data"
}}
"""

        llm = get_llm_for_node("format_data_for_visualization", config)
        response = llm.invoke(
            {"input": prompt, "chat_history": get_chat_history(config)}
        )

        try:
            parser = JsonOutputParser()
            data = parser.parse(str(response.content))

            plotly_data = data.get("plotly_data", {})
            reasoning = data.get("reasoning", "")
            return plotly_data, reasoning
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning(f"LLM data formatting failed: {e}")
            return {}, str(e)

    def _save_as_image(self, fig: go.Figure):
        logger.info("Saving chart as image")

        curr_dir = os.path.dirname(os.path.abspath(__file__))
        img_dir = os.path.join(os.path.dirname(curr_dir), "img")
        os.makedirs(img_dir, exist_ok=True)

        path = os.path.join(img_dir, "chart.png")
        fig.write_image(path, engine="kaleido")
        return path
