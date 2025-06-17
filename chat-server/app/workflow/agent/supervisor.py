from langchain_core.messages import HumanMessage
from langgraph.graph import END
from langgraph.types import Command

from app.workflow.agent.types import State


def supervisor(
    state: State,
) -> Command:
    dataset_ids = state.get("dataset_ids", None)
    project_ids = state.get("project_ids", None)
    messages = state.get("messages", [])

    if messages and isinstance(messages[-1], HumanMessage):
        user_input = str(messages[-1].content)
    else:
        raise Exception("Last Message must be a user message")

    datasets_count = len(dataset_ids) if dataset_ids else 0

    input_state = {
        "messages": state["messages"],
        "dataset_ids": dataset_ids,
        "project_ids": project_ids,
        "user_query": user_input,
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


def dummy_supervisor(state: State) -> Command:
    return Command(goto=END)
