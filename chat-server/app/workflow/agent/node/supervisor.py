from langgraph.types import Command

from ..types import AgentState


def supervisor(
    state: AgentState,
) -> Command:
    dataset_ids = state.get("dataset_ids", None)
    datasets_count = len(dataset_ids) if dataset_ids else 0

    if datasets_count == 1:
        return Command(
            goto="single_dataset_agent",
        )
    else:
        return Command(
            goto="multi_dataset_agent",
        )
