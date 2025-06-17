from app.workflow.agent.types import State


def route_initial_supervisor(state: State) -> str:
    return "visualizer_agent"
