import json

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnableConfig

from app.models.message import IntermediateStep
from app.utils.model_registry.model_provider import (
    get_chat_history,
    get_llm_for_node,
)
from app.workflow.graph.visualize_data_graph.types import State


async def choose_visualization(state: State, config: RunnableConfig) -> dict:
    question = state.get("user_query", "")
    results = state.get("viz_data", [])

    prompt = f"""
    You are a data visualization expert. Given a user's question and query
    results, choose the most appropriate visualization type. Consider the data
    structure, question intent, and best practices for data visualization. Do
    not include any other text in your response.

    User question: {question}
    Query results: {results}

    Choose from these 5 essential visualization types:
    - bar: For categorical comparisons and discrete data
    - line: For trends over time or continuous data progression
    - scatter: For relationships between two continuous variables
    - pie: For part-to-whole relationships (percentages, proportions)
    - histogram: For distribution of a single continuous variable

    Guidelines:
    - Use 'bar' for comparing categories, groups, or discrete values
    - Use 'line' for time series data, trends, or ordered sequences
    - Use 'scatter' for correlation analysis between two variables
    - Use 'pie' for percentages, market share, or composition data
    - Use 'histogram' for frequency distributions or value ranges

    - If the user explicitly provides a visualization type, use that but ensure
      it's one of the above 5 types, otherwise use the most appropriate
      default.

    Respond with JSON containing:
    {{
        "viz_type": "chosen_type",
        "reason": "explanation for why this visualization is appropriate"
    }}
    """

    llm = get_llm_for_node("choose_visualization", config)
    response = await llm.ainvoke(
        {
            "input": prompt,
            "chat_history": get_chat_history(config),
        }
    )

    try:
        parser = JsonOutputParser()
        parsed_response = parser.parse(str(response.content))

        return {
            "viz_type": parsed_response.get("viz_type", "bar"),
            "viz_reason": parsed_response.get("reason", ""),
            "messages": [
                IntermediateStep.from_json(
                    {
                        "content": json.dumps(parsed_response, indent=2),
                    }
                )
            ],
        }
    except Exception as e:
        error_message = f"Error during choosing visualization: {str(e)}"

        return {
            "viz_type": "bar",
            "viz_reason": error_message,
            "messages": [
                IntermediateStep.from_json(
                    {
                        "content": error_message,
                    }
                )
            ],
        }
