from langgraph.types import Command

from ..types import AgentState


def supervisor(
    state: AgentState,
) -> Command:
    dataset_ids = state.get("dataset_ids", None)
    datasets_count = len(dataset_ids) if dataset_ids else 0

    input_state = {
        "user_query": state.get("user_query", "No user input"),
    }

    if datasets_count == 1:
        return Command(
            goto="single_dataset_agent",
            update=input_state,
        )
    else:
        return Command(
            goto="multi_dataset_agent",
            update=input_state,
        )
