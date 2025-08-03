from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableConfig

from app.workflow.graph.multi_dataset_graph.graph import multi_dataset_graph
from app.workflow.graph.multi_dataset_graph.types import InputState
from app.workflow.graph.multi_dataset_graph.types import (
    OutputState as MultiDatasetOutputState,
)
from app.workflow.graph.multi_dataset_graph.types import QueryResult

from ..types import AgentState, Dataset


def list_of_dict_to_list_of_lists(list_of_dict: list[dict]) -> list[list]:
    data = [list(d.values()) for d in list_of_dict]
    headers = list(list_of_dict[0].keys())
    return [headers] + data


def query_result_to_datasets(query_result: QueryResult) -> list[Dataset]:
    """
    Convert a QueryResult object into a list of Dataset objects, each representing the result of a SQL query with its explanation.

    Each Dataset contains tabular data (as a list of lists) and a description combining the SQL query and its explanation. Only SQL queries with results are included.

    Returns:
        List of Dataset objects generated from the query result.
    """
    datasets = []
    dataset_count = 0

    for subquery in query_result.subqueries:
        for sql_query_info in subquery.sql_queries:
            description = f"Query: {sql_query_info.sql_query}\n\n"
            description += f"Explanation: {sql_query_info.explanation}\n\n"
            if sql_query_info.full_sql_result:
                data = list_of_dict_to_list_of_lists(sql_query_info.full_sql_result)
                datasets.append(Dataset(data=data, description=description))
                dataset_count += 1
    return datasets


def transform_output_state(
    output_state: MultiDatasetOutputState,
    state: AgentState,
) -> dict:
    """
    Convert a multi-dataset agent output state into a standardized response dictionary.

    The response includes the original query result, a list of datasets derived from the query result,
    the continue_execution flag, and a single AI message with a placeholder response.
    """
    query_result = output_state.get("query_result", {})
    continue_execution = output_state.get("continue_execution", True)
    datasets = state.get("datasets", []) or []
    datasets.extend(query_result_to_datasets(query_result))

    result = {
        "query_result": query_result,
        "datasets": datasets,
        "continue_execution": continue_execution,
        "messages": [
            AIMessage(content="Successfully processed the user query with multi dataset agent.")
        ],
    }

    return result


async def call_multi_dataset_agent(state: AgentState, config: RunnableConfig) -> dict:
    """
    Asynchronously processes a multi-dataset agent query and returns the transformed response.

    Prepares the input state from the provided agent state and configuration, invokes the multi-dataset graph asynchronously, and transforms the resulting output state into a response dictionary.

    Returns:
        dict: The transformed response containing the query result, datasets, and a placeholder AI message.
    """
    input_state: InputState = {
        "messages": state["messages"],
        "dataset_ids": state["dataset_ids"],
        "project_ids": state["project_ids"],
        "user_query": state["user_query"] or "",
        "relevant_datasets_ids": state.get("relevant_datasets_ids", []),
        "previous_sql_queries": state.get("previous_sql_queries", []),
    }

    output_state = await multi_dataset_graph.ainvoke(input_state, config=config)
    return transform_output_state(output_state=output_state, state=state)  # type: ignore
