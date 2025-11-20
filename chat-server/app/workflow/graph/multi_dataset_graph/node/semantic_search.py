from langchain_core.runnables import RunnableConfig

from app.core.log import custom_logger as logger
from app.models.message import ErrorMessage
from app.services.qdrant.schema_search import search_schemas
from app.utils.model_registry.model_provider import get_model_provider
from app.workflow.events.event_utils import configure_node
from app.workflow.graph.multi_dataset_graph.types import State


@configure_node(
    role="intermediate",
    progress_message="Searching for relevant datasets...",
)
async def semantic_search(state: State, config: RunnableConfig):
    query_index = state.get("subquery_index", 0)
    user_query = state.get("subqueries")[query_index] if state.get("subqueries") else "No input"
    dataset_ids = state.get("dataset_ids", [])
    project_ids = state.get("project_ids", [])
    retry_count = state.get("semantic_search_retry_count", 0)
    missing_context = state.get("missing_dataset_context")

    search_query = user_query
    if missing_context:
        search_query = f"{user_query}\n\nAdditional context: {missing_context}"
        logger.info(f"Semantic search retry with context: {missing_context}")

    try:
        embeddings_model = get_model_provider(config).get_embeddings_model()

        results = await search_schemas(
            user_query=search_query,
            embeddings=embeddings_model,
            dataset_ids=dataset_ids,
            project_ids=project_ids,
        )

        return {
            "semantic_search_results": results,
            "semantic_search_retry_count": retry_count + 1 if missing_context else retry_count,
        }

    except Exception as e:
        err_msg = f"Semantic search failed: {e}"
        logger.exception(err_msg)

        return {
            "semantic_search_results": [],
            "semantic_search_retry_count": retry_count + 1 if missing_context else retry_count,
            "messages": [ErrorMessage(content=err_msg)],
        }
