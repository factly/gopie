from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig

from app.utils.model_registry.model_provider import (
    get_chat_history,
    get_llm_for_node,
)
from app.workflow.graph.single_dataset_graph.types import State


async def response(state: State, config: RunnableConfig) -> dict:
    visualization_result = state.get("viz_result", {})
    query_result = state.get("query_result", {})

    if not query_result:
        return {"messages": [AIMessage(content="No query result found")]}

    user_query = query_result.get("user_query", "")
    dataset_name = query_result.get("dataset_name", "Error occurred")
    sql_queries = query_result.get("sql_queries", [])

    if visualization_result:
        return await visualization_response(
            dataset_name,
            config,
            visualization_result,
            user_query,
            query_result,
        )

    successful_results = [r for r in sql_queries if r.get("success", True)]

    data_context = ""
    if successful_results:
        data_context = "Data from your query:\n"
        for i, result in enumerate(successful_results, 1):
            if result.get("result"):
                data_preview = result["result"]
                data_context += f"Query {i}: {data_preview}\n"

    failed_results = [r for r in sql_queries if not r.get("success", True)]

    if failed_results:
        data_context += "\n\nSome SQL queries were not successful.\n"
        for result in failed_results:
            data_context += f"{result}\n\n"

    prompt = f"""
Answer the user's question: "{user_query}"
Dataset: {dataset_name}

{data_context}

Provide a clear, helpful response based on the available data.
Be conversational and focus on insights.

IMPORTANT: Base your response ONLY on the data provided above. Do not add
information that isn't present in the results.
"""

    llm = get_llm_for_node("response", config)
    response_result = await llm.ainvoke(
        {"input": prompt, "chat_history": get_chat_history(config)}
    )

    return {"messages": [AIMessage(content=str(response_result.content))]}


async def visualization_response(
    dataset_name: str,
    config: RunnableConfig,
    viz_result: dict,
    user_query: str,
    query_result: dict,
) -> dict:
    viz_type = viz_result.get("viz_type", "bar")

    prompt = f"""
The user asked: "{user_query}"
I've created a {viz_type} chart from {dataset_name}.

Visualization result: {viz_result}
SQL queries results: {query_result}

Describe what the visualization shows in a helpful, conversational way.
Focus on key insights and patterns.

IMPORTANT: Base your response ONLY on the data provided above. Do not add
information that isn't present in the results.
"""

    llm = get_llm_for_node("response", config)
    text_response = await llm.ainvoke(
        {"input": prompt, "chat_history": get_chat_history(config)}
    )

    response = {
        "type": "visualization_response",
        "text": str(text_response.content),
        "visualization_result": viz_result,
    }

    return {"messages": [AIMessage(content=str(response))]}
