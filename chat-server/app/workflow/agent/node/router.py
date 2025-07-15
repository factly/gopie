from app.workflow.agent.types import AgentState


def query_router(state: AgentState):
    if state.get("invalid_input", False):
        return "invalid"
    else:
        return "valid"
