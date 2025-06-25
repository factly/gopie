from typing import List

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig

from app.workflow.graph.single_dataset_graph import (
    OutputState as SingleDatasetOutputState,
)
from app.workflow.graph.single_dataset_graph import single_dataset_graph

from ..types import AgentState, Dataset


def list_of_dict_to_list_of_lists(list_of_dict: List[dict]) -> List[List]:
    data = [list(d.values()) for d in list_of_dict]
    headers = list(list_of_dict[0].keys())
    return [headers] + data


def transform_output_state(
    output_state: SingleDatasetOutputState,
) -> AgentState:
    datasets = []
    dataset_count = 0
    query_result = output_state.get("query_result")

    if query_result:
        for sql_query in query_result["sql_queries"]:
            if not sql_query["result"]:
                continue
            description = f"Dataset {dataset_count}\n\n"
            description += f"Query: {sql_query['sql_query']}\n\n"
            description += f"Explanation: {sql_query['explanation']}\n\n"
            data = list_of_dict_to_list_of_lists(sql_query["result"])
            datasets.append(Dataset(data=data, description=description))
            dataset_count += 1

    response_text = output_state.get("response_text", "No response")
    return {
        "datasets": datasets,
        "messages": [AIMessage(content=response_text)],
    }


async def call_single_dataset_agent(
    state: AgentState, config: RunnableConfig
) -> AgentState:
    input_state = {
        "messages": state["messages"],
        "dataset_id": state["dataset_ids"][0],
        "user_query": state["user_query"],
    }

    output_state = await single_dataset_graph.ainvoke(
        input_state, config=config
    )
    return transform_output_state(output_state)
