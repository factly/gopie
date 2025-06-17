from langgraph.types import Command

from app.workflow.graph.single_dataset_graph.types import State


async def transfer_visual_call(state: State) -> Command:
    user_query = state.get("user_query", "")

    all_data = []
    for result in state.get("sql_queries", []):
        if result.get("result"):
            all_data.extend(result["result"])

    input_state = {
        "messages": state["messages"],
        "user_query": user_query,
        "viz_data": all_data,
        "query_result": state.get("query_result", {}),
    }

    return Command(
        goto="visualizer_agent",
        graph=Command.PARENT,
        update=input_state,
    )
