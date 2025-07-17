from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig

from app.workflow.graph.single_dataset_graph.graph import single_dataset_graph
from app.workflow.graph.single_dataset_graph.types import (
    OutputState as SingleDatasetOutputState,
    InputState,
)
from app.models.query import QueryResult, SingleDatasetQueryResult

from app.models.query import SingleDatasetQueryResult
from ..types import AgentState, Dataset


def list_of_dict_to_list_of_lists(list_of_dict: list[dict]) -> list[list]:
    data = [list(d.values()) for d in list_of_dict]
    headers = list(list_of_dict[0].keys())
    return [headers] + data


def transform_output_state(
    output_state: SingleDatasetOutputState,
) -> AgentState | dict:
    datasets = []
    dataset_count = 0
    query_result: QueryResult = output_state.get("query_result")

    result: SingleDatasetQueryResult | None = query_result.single_dataset_query_result

    if result is not None:
        sql_results = result.sql_results
        if sql_results is not None:
            for sql_query_info in sql_results:
                if not sql_query_info.sql_query_result:
                    continue
                description = f"Dataset {dataset_count}\n\n"
                description += f"Query: {sql_query_info.sql_query}\n\n"
                description += f"Explanation: {sql_query_info.explanation}\n\n"
                data = list_of_dict_to_list_of_lists(sql_query_info.sql_query_result)
                datasets.append(Dataset(data=data, description=description))
                dataset_count += 1

    response_text = "No response"
    return {
        "query_result": query_result,
        "datasets": datasets,
        "messages": [AIMessage(content=response_text)],
    }


async def call_single_dataset_agent(state: AgentState, config: RunnableConfig) -> dict:
    dataset_ids = state.get("dataset_ids", [])
    dataset_id = dataset_ids[0] if dataset_ids else None
    user_query = state.get("user_query", "") or ""

    input_state: InputState = {
        "messages": state["messages"],
        "dataset_id": dataset_id,
        "user_query": user_query,
    }

    output_state = await single_dataset_graph.ainvoke(input_state, config=config)
    return transform_output_state(output_state)  # type: ignore
