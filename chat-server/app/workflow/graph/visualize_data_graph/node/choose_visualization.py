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
    """
    Choose the appropriate visualization type based on the data and question.
    This runs in parallel with format_results.
    """
    question = state.get("user_query", "")
    results = state.get("visualization_data", [])

    prompt = f"""
    You are a data visualization expert. Given a user's question and query
    results, choose the most appropriate visualization type. Consider the data
    structure, question intent, and best practices for data visualization. Do
    not include any other text in your response.

    User question: {question}
    Query results: {results}

    Choose from these visualization types:
    - bar: For categorical comparisons
    - line: For trends over time or continuous data
    - scatter: For relationships between two continuous variables
    - pie: For part-to-whole relationships
    - horizontal_bar: For categorical data with long labels

    Respond with JSON containing:
    {{
        "visualization_type": "chosen_type",
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
            "visualization_type": parsed_response.get(
                "visualization_type", "bar"
            ),
            "visualization_reason": parsed_response.get("reason", ""),
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
            "visualization_type": "bar",
            "visualization_reason": error_message,
            "messages": [
                IntermediateStep.from_json(
                    {
                        "content": error_message,
                    }
                )
            ],
        }
