from langgraph.types import Command

from ..types import AgentState


def supervisor(
    state: AgentState,
) -> Command:
    dataset_ids = state.get("dataset_ids", None)
    datasets_count = len(dataset_ids) if dataset_ids else 0
    datasets = state.get("datasets", [])
    needs_visualization = state.get("needs_visualization", False)
    if datasets and needs_visualization:
        return Command(
            goto="visualization_agent",
        )
    elif datasets_count == 1:
        return Command(
            goto="single_dataset_agent",
        )
    else:
        return Command(
            goto="multi_dataset_agent",
        )
