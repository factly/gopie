from langchain_core.callbacks.manager import adispatch_custom_event
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnableConfig

from app.core.constants import DATASETS_USED
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
    user_query = (
        state.get("subqueries")[query_index]
        if state.get("subqueries")
        else "No input"
    )
    query_result = state.get("query_result", {})
    dataset_ids = state.get("dataset_ids", [])
    project_ids = state.get("project_ids", [])

    need_semantic_search = state.get("need_semantic_search", True)
    required_dataset_ids = state.get("required_dataset_ids", [])

    query_type = query_result.subqueries[query_index].query_type
    confidence_score = query_result.subqueries[query_index].confidence_score

    try:
        llm = get_model_provider(config).get_llm_for_node("identify_datasets")
        embeddings_model = get_model_provider(config).get_embeddings_model()

        required_dataset_schemas = await get_schema_by_dataset_ids(
            required_dataset_ids
        )

        semantic_searched_datasets = []
        if need_semantic_search or not required_dataset_schemas:
            try:
                semantic_searched_datasets = await search_schemas(
                    user_query,
                    embeddings_model,
                    dataset_ids=dataset_ids,
                    project_ids=project_ids,
                )
            except Exception as e:
                logger.warning(
                    f"Vector search error: {e!s}. Unable to retrieve dataset "
                    "information."
                )

        if not required_dataset_schemas and not semantic_searched_datasets:
            query_result.set_node_message(
                "identify_datasets",
                {
                    "No relevant datasets found by doing semantic search or "
                    "required datasets from previous messages. This query is "
                    "not relavant to any datasets. Treating as conversational "
                    "query."
                },
            )

            await adispatch_custom_event(
                "gopie-agent",
                {"content": "No relevant datasets found"},
            )

            # convert data_query to conversational if no datasets found
            if query_type == "data_query":
                query_result.subqueries[
                    query_index
                ].query_type = "conversational"

            return {
                "query_result": query_result,
                "identified_datasets": None,
                "messages": [
                    IntermediateStep.from_json(
                        {
                            "error": (
                                "No relevant datasets found. "
                                "Treating as conversational query."
                            )
                        }
                    )
                ],
            }

        llm_prompt = get_prompt(
            "identify_datasets",
            user_query=user_query,
            required_dataset_schemas=required_dataset_schemas,
            semantic_searched_datasets=semantic_searched_datasets,
            confidence_score=confidence_score,
            query_type=query_type,
        )

        response = await llm.ainvoke(llm_prompt)

        response_content = str(response.content)
        parser = JsonOutputParser()
        parsed_content = parser.parse(response_content)

        selected_datasets = parsed_content.get("selected_dataset", [])
        selected_datasets.extend(
            [schema.dataset_name for schema in required_dataset_schemas]
        )
        query_result.subqueries[query_index].tables_used = selected_datasets

        column_assumptions = parsed_content.get("column_assumptions", [])
        node_message = parsed_content.get("node_message")

        # Convert conversational query to data_query if relevant datasets found
        if query_type == "conversational" and selected_datasets:
            query_result.subqueries[query_index].query_type = "data_query"

        if node_message:
            query_result.set_node_message("identify_datasets", node_message)

        all_available_schemas = (
            required_dataset_schemas + semantic_searched_datasets
        )

        filtered_dataset_schemas = [
            schema
            for schema in all_available_schemas
            if schema.dataset_name in selected_datasets
        ]

        selected_dataset_ids = [
            schema.dataset_id for schema in filtered_dataset_schemas
        ]

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
                "values": {"datasets": selected_dataset_ids},
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
            "messages": [ErrorMessage.from_json({"error": error_msg})],
        }


def route_from_datasets(state: State) -> str:
    """
    Route to the appropriate next node based on dataset identification results.

    This function determines whether to proceed with data analysis or
    route directly to response generation for conversational queries.
    """

    query_result = state.get("query_result")
    query_index = state.get("subquery_index", 0)
    last_message = (
        state.get("messages", [])[-1] if state.get("messages") else None
    )

    query_type = query_result.subqueries[query_index].query_type
    identified_datasets = state.get("identified_datasets")

    if isinstance(last_message, ErrorMessage):
        return "analyze_dataset"

    if query_type == "conversational" or not identified_datasets:
        return "no_datasets_found"
    else:
        return "analyze_dataset"
