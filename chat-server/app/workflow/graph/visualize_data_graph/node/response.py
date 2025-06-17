from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig

from app.utils.model_registry.model_provider import (
    get_chat_history,
    get_llm_for_node,
)
from app.workflow.graph.visualize_data_graph.types import State


async def visualization_response(
    state: State,
    config: RunnableConfig,
) -> dict:
    viz_type = state.get("viz_type", "bar")
    user_query = state.get("user_query", "")
    viz_result = state.get("formatted_viz_data", {})
    query_result = state.get("query_result", {})

    prompt = f"""
The user asked: "{user_query}"
I've created a {viz_type} chart.

Visualization result: {viz_result}
SQL queries results: {query_result}

Describe what the visualization shows in a helpful, conversational way.
Focus on key insights and patterns.

IMPORTANT: Base your response ONLY on the data provided above. Do not add
information that isn't present in the results.
"""

    llm = get_llm_for_node("visualization_response", config)
    text_response = await llm.ainvoke(
        {"input": prompt, "chat_history": get_chat_history(config)}
    )

    response = {
        "type": "visualization_response",
        "text": str(text_response.content),
        "visualization_result": viz_result,
    }
    return {"messages": [AIMessage(content=str(response))]}
