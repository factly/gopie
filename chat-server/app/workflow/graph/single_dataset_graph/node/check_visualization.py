from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnableConfig

from app.core.log import logger
from app.utils.model_registry.model_provider import (
    get_chat_history,
    get_llm_for_node,
)
from app.workflow.graph.single_dataset_graph.types import State


async def check_visualization(state: State, config: RunnableConfig) -> dict:
    user_query = state.get("user_query", "")

    prompt = f"""
You are a routing supervisor for a data analysis system.
Analyze the user's question to determine if they want data
visualization (charts, graphs, plots) or just a text
response.
Consider visualization keywords like: plot, chart, graph,
visualize, show, display, trend, comparison, distribution,
etc.

User question: {user_query}
Respond with JSON:
{{
    "wants_visualization": true/false,
    "reasoning": "explanation of the decision"
}}
    """
    llm = get_llm_for_node("supervisor", config)
    response = await llm.ainvoke(
        {
            "input": prompt,
            "chat_history": get_chat_history(config),
        }
    )

    try:
        parser = JsonOutputParser()
        parsed_response = parser.parse(str(response.content))
        wants_visualization = parsed_response.get("wants_visualization", False)

        return {
            "wants_visualization": wants_visualization,
            "reasoning": parsed_response.get("reasoning", ""),
        }
    except Exception as e:
        logger.error(f"Error parsing check_visualization response: {e}")
        return {"wants_visualization": False, "reasoning": ""}


def route_next_node(state: State, config: RunnableConfig) -> str:
    wants_visualization = state.get("wants_visualization", False)
    if wants_visualization:
        return "handoff_to_visualizer_agent"
    else:
        return "response"
