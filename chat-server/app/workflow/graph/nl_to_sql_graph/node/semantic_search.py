from langchain_core.runnables import RunnableConfig

from app.services.qdrant.schema_search import search_schemas
from app.utils.model_registry.model_provider import get_model_provider
from app.workflow.graph.nl_to_sql_graph.types import State


async def semantic_search(state: State, config: RunnableConfig):
    user_query = state.get("user_query", "")
    dataset_ids = state.get("dataset_ids") or []
    project_ids = state.get("project_ids") or []

    embeddings_model = get_model_provider(config).get_embeddings_model()

    results = await search_schemas(
        user_query=user_query,
        embeddings=embeddings_model,
        dataset_ids=dataset_ids,
        project_ids=project_ids,
    )

    return {"semantic_search_results": results}
