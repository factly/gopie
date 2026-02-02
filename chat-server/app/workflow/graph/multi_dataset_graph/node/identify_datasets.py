from langchain_core.callbacks.manager import adispatch_custom_event
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from app.core.constants import DATASETS_USED, DATASETS_USED_ARG
from app.core.log import custom_logger as logger
from app.models.message import ErrorMessage, IntermediateStep
from app.services.qdrant.get_schema import get_schema_by_dataset_ids
from app.utils.langsmith.prompt_manager import get_prompt_llm_chain
from app.workflow.events.event_utils import (
    configure_node,
    fake_streaming_response,
)
from app.workflow.graph.multi_dataset_graph.types import State
from app.workflow.graph.sql_planner_graph.types import (
    ColumnAssumptions,
    DatasetsInfo,
)


def _create_empty_datasets_info() -> DatasetsInfo:
    """Create an empty DatasetsInfo object for error scenarios."""
    return DatasetsInfo(
        schemas=[],
        column_assumptions=None,
        correct_column_requirements=None,
    )


class IdentifyDatasetsOutput(BaseModel):
    selected_dataset: list[str] = Field(
        description="Selected dataset names from available options", default=[]
    )
    reasoning: str = Field(description="Explanation why these specific datasets were selected")
    column_assumptions: list[ColumnAssumptions] = Field(
        description="Column assumptions for selected datasets", default=[]
    )
    node_message: str = Field(description="Brief message about selected datasets and their sources")
    status_message: str = Field(
        description="Status message about the progress of the identify_datasets node"
    )
    missing_requirements: str | None = Field(
        description="""
        If selected datasets DO NOT contain all necessary data to fully answer the user query,
        describe what TYPE of data or relationships are missing. Be specific about the DATA CONCEPT
        needed, not necessarily exact table names. Examples: 'need order/purchase data linked to
        customers', 'missing product information to complete order details', 'require transaction
        history connected via user reference'. Focus on describing the relationship and data domain.
        Leave EMPTY if the selected datasets can fully answer the query.""",
        default=None,
    )


@configure_node(
    role="intermediate",
    progress_message="Identifying datasets...",
)
async def identify_datasets(state: State, config: RunnableConfig) -> dict:
    """
    Identify relevant dataset based on natural language query.

    This function can also potentially reclassify a query based on vector
    search results:
    - If no datasets found for a data_query → convert to conversational
    - If high relevance datasets found for low confidence query →
        confirm as data_query

    Three scenarios are handled:
    1. Use only required_dataset_ids (automatically selected, need column
       assumptions)
    2. Use required_dataset_ids + semantic search (required are auto-selected,
       LLM can choose additional from semantic search)
    3. Use semantic search only (LLM chooses from semantic search results)
    """
    query_index = state.get("subquery_index", 0)
    user_query = state.get("subqueries")[query_index] if state.get("subqueries") else "No input"
    query_result = state.get("query_result", {})
    validation_result = state.get("validation_result", None)
    relevant_datasets_ids = state.get("relevant_datasets_ids", [])

    try:
        relevant_dataset_schemas = await get_schema_by_dataset_ids(
            dataset_ids=relevant_datasets_ids
        )

        semantic_searched_datasets = state.get("semantic_search_results", [])

        if not semantic_searched_datasets:
            query_result.set_node_message(
                "identify_datasets",
                {
                    "No relevant datasets found by doing semantic search. This subquery is "
                    "not relevant to any datasets. Treating as conversational query."
                },
            )

            await adispatch_custom_event(
                "gopie-agent",
                {"content": "No relevant datasets found"},
            )

            return {
                "query_result": query_result,
                "identified_datasets": None,
                "datasets_info": _create_empty_datasets_info(),
                "messages": [
                    ErrorMessage(
                        content="No relevant datasets found for the query, ask user to rephrase or ask more relevant query"
                    )
                ],
            }

        chain_input = {
            "user_query": user_query,
            "relevant_dataset_schemas": relevant_dataset_schemas,
            "semantic_searched_datasets": semantic_searched_datasets,
            "validation_result": validation_result,
        }

        chain = get_prompt_llm_chain(
            "identify_datasets",
            config,
            schema=IdentifyDatasetsOutput,
        )
        response = await chain.ainvoke(chain_input)

        selected_datasets = response.selected_dataset
        if query_result.subqueries and len(query_result.subqueries) > query_index:
            query_result.subqueries[query_index].tables_used = selected_datasets
            if not selected_datasets:
                query_result.subqueries[query_index].add_error_message(
                    "No relevant datasets found for the query, ask user to rephrase or ask more relevant query",
                    "identify_datasets",
                )

        column_assumptions = response.column_assumptions
        node_message = response.node_message
        status_message = response.status_message

        if node_message:
            query_result.set_node_message("identify_datasets", node_message)

        all_available_schemas = relevant_dataset_schemas + semantic_searched_datasets

        filtered_dataset_schemas = [
            schema for schema in all_available_schemas if schema.dataset_name in selected_datasets
        ]

        selected_dataset_ids = [schema.dataset_id for schema in filtered_dataset_schemas]

        datasets_info = DatasetsInfo(
            schemas=filtered_dataset_schemas,
            column_assumptions=column_assumptions,
            correct_column_requirements=None,
        )

        if status_message:
            await fake_streaming_response(status_message, config)

        await adispatch_custom_event(
            "gopie-agent",
            {
                "content": "Datasets identified",
                "name": DATASETS_USED,
                "values": {DATASETS_USED_ARG: selected_dataset_ids},
            },
        )

        return {
            "query_result": query_result,
            "datasets_info": datasets_info,
            "identified_datasets": selected_datasets,
            "missing_dataset_context": response.missing_requirements,
            "messages": [IntermediateStep(content=node_message)],
        }

    except Exception as e:
        error_msg = f"Failed to identify datasets for query '{user_query}': {e!s}"
        query_result.add_error_message(
            str(e), f"Error in identify_datasets node (subquery index: {query_index})"
        )
        await adispatch_custom_event(
            "gopie-agent",
            {"content": f"Error identifying datasets: {type(e).__name__}"},
        )

        logger.exception(f"Dataset identification failed - Query: '{user_query}', Error: {e!s}")

        return {
            "query_result": query_result,
            "identified_datasets": None,
            "datasets_info": _create_empty_datasets_info(),
            "messages": [ErrorMessage(content=error_msg)],
        }


def route_from_datasets(state: State) -> str:
    """
    Route to the appropriate next node based on dataset identification results.

    Returns:
        str: One of "no_datasets_found", "retry_semantic_search", or "analyze_dataset"
    """
    last_message = state.get("messages", [])[-1] if state.get("messages") else None
    identified_datasets = state.get("identified_datasets")
    semantic_search_retry_count = state.get("semantic_search_retry_count", 0)
    missing_dataset_context = state.get("missing_dataset_context")

    if isinstance(last_message, ErrorMessage):
        return "no_datasets_found"

    if missing_dataset_context and semantic_search_retry_count < 1:
        return "retry_semantic_search"

    if not identified_datasets:
        return "no_datasets_found"

    return "plan_query"
