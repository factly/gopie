from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnableConfig

from app.utils.langsmith.prompt_manager import get_prompt
from app.utils.model_registry.model_provider import get_model_provider
from app.workflow.events.event_utils import configure_node
from app.workflow.graph.visualize_data_graph.graph import (
    graph as visualize_data_graph,
)

from ..types import AgentState


@configure_node(
    role="intermediate",
    progress_message="Checking visualization needs...",
)
async def check_visualization(state: AgentState, config: RunnableConfig) -> dict:
    """
    Determine if the user's query requires data visualization by querying a language model.
    
    Returns:
        dict: A dictionary with a boolean value under the key 'needs_visualization' indicating whether visualization is needed.
    """
    user_input = state.get("user_query", "")
    prompt_messages = get_prompt(
        "check_visualization",
        user_query=user_input,
    )

    llm = get_model_provider(config).get_llm_for_node("check_visualization")
    response = await llm.ainvoke(prompt_messages)

    parser = JsonOutputParser()
    parsed_response = parser.parse(str(response.content))
    needs_visualization = parsed_response.get("wants_visualization", False)
    return {"needs_visualization": needs_visualization}


async def call_visualization_agent(state: AgentState, config: RunnableConfig) -> AgentState | None:
    """
    Invoke the visualization agent to process the user query and datasets.
    
    This function asynchronously calls the data graph visualization agent using the current user query and datasets from the agent state. It does not return a value.
    """
    input_state = {
        "user_query": state.get("user_query", ""),
        "datasets": state.get("datasets", []),
    }

    _ = await visualize_data_graph.ainvoke(input_state, config=config)


async def should_visualize(state: AgentState):
    """
    Determine the next workflow step based on whether visualization is needed and datasets are available.
    
    Returns:
        str: "visualization_agent" if visualization is required and datasets exist; otherwise, "generate_result".
    """
    if state.get("needs_visualization", False) and state.get("datasets", []):
        return "visualization_agent"
    else:
        return "generate_result"
