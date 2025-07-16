from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig

from app.workflow.graph.multi_dataset_graph.graph import multi_dataset_graph
from app.workflow.graph.multi_dataset_graph.types import (
    OutputState as MultiDatasetOutputState,
    InputState,
)
from app.workflow.graph.multi_dataset_graph.types import QueryResult

from ..types import AgentState, Dataset


def list_of_dict_to_list_of_lists(list_of_dict: list[dict]) -> list[list]:
    data = [list(d.values()) for d in list_of_dict]
    headers = list(list_of_dict[0].keys())
    return [headers] + data


def query_result_to_datasets(query_result: QueryResult) -> list[Dataset]:
    datasets = []
    dataset_count = 0

    for subquery in query_result.subqueries:
        for sql_query_info in subquery.sql_queries:
            description = f"Query: {sql_query_info.sql_query}\n\n"
            description += f"Explanation: {sql_query_info.explanation}\n\n"
            if sql_query_info.sql_query_result:
                data = list_of_dict_to_list_of_lists(sql_query_info.sql_query_result)
                datasets.append(Dataset(data=data, description=description))
                dataset_count += 1
    return datasets


def transform_output_state(
    output_state: MultiDatasetOutputState,
) -> dict:
    query_result = output_state.get("query_result", {})
    datasets = query_result_to_datasets(query_result)
    response_text = "No response"
    return {
        "query_result": query_result,
        "datasets": datasets,
        "messages": [AIMessage(content=response_text)],
    }


async def call_multi_dataset_agent(state: AgentState, config: RunnableConfig) -> dict:
    input_state: InputState = {
        "messages": state["messages"],
        "dataset_ids": state["dataset_ids"],
        "project_ids": state["project_ids"],
        "user_query": state["user_query"] or "",
        "need_semantic_search": state.get("need_semantic_search", True),
        "required_dataset_ids": state.get("required_dataset_ids", []),
    }

    output_state = await multi_dataset_graph.ainvoke(input_state, config=config)
    return transform_output_state(output_state)  # type: ignore
