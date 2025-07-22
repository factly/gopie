from langgraph.types import Command

from ..types import AgentState


def supervisor(
    state: AgentState,
) -> Command:
    dataset_ids = state.get("dataset_ids", None)
    datasets_count = len(dataset_ids) if dataset_ids else 0
    visualization_data = state.get("visualization_data", [])
    new_data_needed = state.get("new_data_needed", False)
    needs_visualization = state.get("needs_visualization", False)
    previous_json_paths = state.get("previous_json_paths", [])

    if not new_data_needed and (visualization_data or needs_visualization or previous_json_paths):
        return Command(
            goto="visualization_agent",
        )
    else:
        if datasets_count == 1:
            return Command(
                goto="single_dataset_agent",
            )
        else:
            return Command(
                goto="multi_dataset_agent",
            )
