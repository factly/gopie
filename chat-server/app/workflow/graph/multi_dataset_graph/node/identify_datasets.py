from langchain_core.callbacks.manager import adispatch_custom_event
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnableConfig

from app.core.constants import DATASETS_USED, DATASETS_USED_ARG
from app.core.log import logger
from app.models.message import ErrorMessage, IntermediateStep
from app.services.qdrant.get_schema import get_schema_by_dataset_ids
from app.services.qdrant.schema_search import search_schemas
from app.utils.langsmith.prompt_manager import get_prompt
from app.utils.model_registry.model_provider import get_model_provider
from app.workflow.events.event_utils import configure_node
from app.workflow.graph.multi_dataset_graph.types import DatasetsInfo, State


@configure_node(
    role="intermediate",
    progress_message="Identifying datasets...",
)
async def identify_datasets(state: State, config: RunnableConfig):
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
    dataset_ids = state.get("dataset_ids", [])
    project_ids = state.get("project_ids", [])

    last_message = state.get("messages", [])[-1]

    relevant_datasets_ids = state.get("relevant_datasets_ids", [])

    try:
        llm = get_model_provider(config).get_llm_for_node("identify_datasets")
        embeddings_model = get_model_provider(config).get_embeddings_model()

        relevant_dataset_schemas = await get_schema_by_dataset_ids(
            dataset_ids=relevant_datasets_ids
        )

        semantic_searched_datasets = []
        try:
            semantic_searched_datasets = await search_schemas(
                user_query=user_query,
                embeddings=embeddings_model,
                dataset_ids=dataset_ids,
                project_ids=project_ids,
            )
        except Exception as e:
            logger.warning(f"Vector search error: {e!s}. Unable to retrieve dataset information.")

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
                "messages": [IntermediateStep(content="No relevant datasets found")],
            }

        llm_prompt = get_prompt(
            "identify_datasets",
            user_query=user_query,
            relevant_dataset_schemas=relevant_dataset_schemas,
            semantic_searched_datasets=semantic_searched_datasets,
        )

        response = await llm.ainvoke(llm_prompt + [last_message])

        response_content = str(response.content)
        parser = JsonOutputParser()
        parsed_content = parser.parse(response_content)

        selected_datasets = parsed_content.get("selected_dataset", [])
        query_result.subqueries[query_index].tables_used = selected_datasets

        column_assumptions = parsed_content.get("column_assumptions", [])
        node_message = parsed_content.get("node_message")

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
            "messages": [IntermediateStep.from_json(parsed_content)],
        }

    except Exception as e:
        error_msg = f"Error identifying datasets: {e!s}"
        query_result.add_error_message(str(e), "Error identifying datasets")

        await adispatch_custom_event(
            "gopie-agent",
            {"content": "Error identifying datasets"},
        )

        return {
            "query_result": query_result,
            "identified_datasets": None,
            "messages": [ErrorMessage(content=error_msg)],
        }


def route_from_datasets(state: State) -> str:
    """
    Route to the appropriate next node based on dataset identification results.

    This function determines whether to proceed with data analysis or
    route directly to response generation for conversational queries.
    """

    last_message = state.get("messages", [])[-1] if state.get("messages") else None
    identified_datasets = state.get("identified_datasets")

    if isinstance(last_message, ErrorMessage):
        return "analyze_dataset"

    if not identified_datasets:
        return "no_datasets_found"
    else:
        return "analyze_dataset"
