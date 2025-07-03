from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnableConfig

from app.utils.langsmith.prompt_manager import get_prompt
from app.utils.model_registry.model_provider import get_model_provider
from app.workflow.events.event_utils import configure_node
from app.workflow.graph.visualize_data_graph import (
    graph as visualize_data_graph,
)

from ..types import AgentState


@configure_node(
    role="intermediate",
    progress_message="Checking visualization needs...",
)
async def check_visualization(
    state: AgentState, config: RunnableConfig
) -> dict:
    messages = state.get("messages", [])
    user_query = str(messages[-1].content)
    prompt_messages = get_prompt(
        "check_visualization",
        user_query=user_query,
    )

    llm = get_model_provider(config).get_llm_for_node("check_visualization")
    response = await llm.ainvoke(prompt_messages)

    parser = JsonOutputParser()
    parsed_response = parser.parse(str(response.content))
    needs_visualization = parsed_response.get("wants_visualization", False)
    return {"needs_visualization": needs_visualization}


async def call_visualization_agent(
    state: AgentState, config: RunnableConfig
) -> AgentState | None:
    visualization_data = state.get("visualization_data", None)

    viz_data = []

    if visualization_data:
        viz_data = visualization_data
    else:
        viz_data = state.get("datasets", [])

    input_state = {
        "user_query": state.get("user_query", ""),
        "datasets": viz_data,
    }

    _ = await visualize_data_graph.ainvoke(input_state, config=config)
