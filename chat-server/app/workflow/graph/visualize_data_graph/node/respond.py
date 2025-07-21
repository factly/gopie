from app.utils.model_registry.model_provider import get_model_provider
from app.workflow.events.event_utils import configure_node
from ...visualize_data_graph.types import State
from langchain_core.runnables import RunnableConfig

@configure_node(
    role="ai",
    progress_message="",
)
async def respond(state: State, config: RunnableConfig) -> dict:
    llm = get_model_provider(config).get_llm_for_node("visualize_data")

    prompt = """
You are a data visualization assistant. Your task is to provide a concise, natural response about the visualization results.

Given the visualization result data and any potential errors, analyze the outcome and provide a brief, user-friendly summary.

Guidelines:
- Keep the response short and natural (2-3 sentences maximum)
- Focus specifically on the visualization outcome
- If visualization data was successfully generated, briefly describe what was created
- If there are errors, don't expose technical details - simply inform the user that something went wrong during visualization generation
- Maintain a helpful and professional tone
- This is a sub-result, so keep it concise

Visualization Result:
Data paths: {data}
Errors (if any): {errors}

User Query: {user_query}

Provide a brief, natural response about the visualization results:
"""

    result = state["result"]
    user_query = state["user_query"]

    formatted_prompt = prompt.format(
        data=result.data if result.data else "No visualization data generated",
        errors=result.errors if result.errors else "None",
        user_query=user_query
    )

    response = await llm.ainvoke(formatted_prompt)

    return {"messages": [response]}