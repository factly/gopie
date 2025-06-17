from app.workflow.agent.types import State


def route_visualization_supervisor(state: State) -> str:
    return "visualizer_agent"
