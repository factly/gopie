import json

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig

from app.utils.model_registry.model_provider import get_configured_llm_for_node
from app.workflow.events.event_utils import configure_node

from ...visualize_data_graph.types import State


@configure_node(
    role="ai",
    progress_message="",
)
async def respond(state: State, config: RunnableConfig) -> dict:
    result = state["result"]
    errors = getattr(result, "errors", []) or []
    visualizations = getattr(result, "data", []) or []

    user_query = state.get("user_query") or "your request"
    datasets = state.get("datasets") or []
    dataset_descriptions = [d.description for d in datasets if getattr(d, "description", None)]
    relevant_sql_queries = state.get("relevant_sql_queries") or []
    result_images_b64 = state.get("result_images_b64", []) or []

    status = "success" if visualizations and not errors else "error"
    context_payload = {
        "status": status,
        "user_query": user_query,
        "num_visualizations": len(visualizations),
        "datasets": dataset_descriptions[:3],
        "relevant_sql_queries_count": len(relevant_sql_queries),
        "errors": errors[:2],
    }

    system_message = SystemMessage(
        content=(
            """You are a helpful assistant in a developer tool.
            Write one concise, friendly message that summarizes the outcome of a data visualization request.
            Rules:
            - Keep it to 1-2 sentences.
            - Do not use markdown or quotes.
            - If status is success: mention the number of visualizations, optionally list up to 3 dataset descriptions if present,
            and say they can be viewed in the result tab. If relevant_sql_queries_count > 0, you may mention that they were considered.
            - If status is error: briefly say you ran into an error and could not generate visualizations, include a short error hint if available,
            and suggest rephrasing or narrowing the request."""
        )
    )
    if result_images_b64:
        human_message = HumanMessage(
            content=[
                {
                    "type": "text",
                    "text": "Here are the visualization results.",
                },
                {
                    "type": "image",
                    "source_type": "base64",
                    "data": result_images_b64[0],
                    "mime_type": "image/png",
                },
                {
                    "type": "text",
                    "text": f"Context: {json.dumps(context_payload, ensure_ascii=False)}",
                },
            ]
        )
    else:
        human_message = HumanMessage(
            content=f"Here are the visualization results. Context: {json.dumps(context_payload, ensure_ascii=False)}"
        )

    llm = get_configured_llm_for_node("response", config)
    response = await llm.ainvoke([system_message, human_message])
    return {"messages": [AIMessage(content=str(response.content))]}
