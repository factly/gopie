from app.workflow.agent.types import AgentState


def query_router(state: AgentState):
    """
    Determine whether the agent state represents valid or invalid input.

    Returns:
        str: "invalid" if the "invalid_input" key in the state is True, otherwise "valid".
    """
    if state.get("invalid_input", False):
        return "invalid"
    else:
        return "valid"
