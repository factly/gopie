from langgraph.types import Command

from app.workflow.graph.nl_to_sql_graph.types import State


def supervisor(state: State) -> Command:
    dataset_ids = state.get("dataset_ids") or []
    project_ids = state.get("project_ids") or []

    if len(dataset_ids) == 1 and len(project_ids) <= 1:
        return Command(goto="sql_agent")

    return Command(goto="semantic_search")
