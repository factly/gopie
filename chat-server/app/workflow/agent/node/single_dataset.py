from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig

from app.models.query import QueryResult, SingleDatasetQueryResult
from app.workflow.graph.single_dataset_graph.graph import single_dataset_graph
from app.workflow.graph.single_dataset_graph.types import InputState
from app.workflow.graph.single_dataset_graph.types import (
    OutputState as SingleDatasetOutputState,
)

from ..types import AgentState, Dataset


def list_of_dict_to_list_of_lists(list_of_dict: list[dict]) -> list[list]:
    data = [list(d.values()) for d in list_of_dict]
    headers = list(list_of_dict[0].keys())
    return [headers] + data


def transform_output_state(output_state: SingleDatasetOutputState, state: AgentState) -> dict:
    """
    Processes the output state from a single dataset agent workflow and formats the query results for downstream consumption.

    Extracts the query result and, if available, iterates over SQL query results to construct a list of datasets
    with descriptions and tabular data. Returns a dictionary containing the original query result, the list of datasets, and a default AI message.
    """
    datasets = state.get("datasets", []) or []
    dataset_count = 0
    query_result: QueryResult = output_state.get("query_result")

    result: SingleDatasetQueryResult | None = query_result.single_dataset_query_result

    if result is not None:
        sql_results = result.sql_results
        if sql_results is not None:
            for sql_query_info in sql_results:
                if not sql_query_info.full_sql_result:
                    continue
                description = f"Dataset {dataset_count}\n\n"
                description += f"Query: {sql_query_info.sql_query}\n\n"
                description += f"Explanation: {sql_query_info.explanation}\n\n"
                data = list_of_dict_to_list_of_lists(sql_query_info.full_sql_result)
                datasets.append(Dataset(data=data, description=description))
                dataset_count += 1

    return {
        "query_result": query_result,
        "datasets": datasets,
        "messages": [
            AIMessage(content="Successfully processed the user query with single dataset agent.")
        ],
    }


async def call_single_dataset_agent(state: AgentState, config: RunnableConfig) -> dict:
    """
    Asynchronously invokes the single dataset agent workflow with the provided state and configuration, returning the processed output as a dictionary.

    Parameters:
        state (AgentState): The current agent state containing messages, dataset IDs, and user query.
        config (RunnableConfig): Configuration for the workflow execution.

    Returns:
        dict: The transformed output state containing query results and related dataset information.
    """
    dataset_ids = state.get("dataset_ids", [])
    dataset_id = dataset_ids[0] if dataset_ids else None
    user_query = state.get("user_query", "") or ""

    input_state: InputState = {
        "messages": state["messages"],
        "dataset_id": dataset_id,
        "user_query": user_query,
        "previous_sql_queries": state.get("previous_sql_queries", []),
    }

    output_state = await single_dataset_graph.ainvoke(input_state, config=config)
    return transform_output_state(output_state=output_state, state=state)  # type: ignore
