import asyncio
from uuid import uuid4

from qdrant_client.http.models import FieldCondition, Filter, MatchValue

from app.core.config import settings
from app.core.log import logger
from app.services.qdrant.qdrant_setup import (
    initialize_qdrant_client,
    setup_vector_store,
)
from app.utils.model_registry.model_provider import get_model_provider


async def add_document_to_vector_store(document):
    vector_store = setup_vector_store(
        get_model_provider().get_embeddings_model()
    )
    client = initialize_qdrant_client()

    project_id = document.metadata["project_id"]
    dataset_id = document.metadata["dataset_id"]

    search_result = client.scroll(
        collection_name=settings.QDRANT_COLLECTION,
        scroll_filter=Filter(
            must=[
                FieldCondition(
                    key="metadata.project_id",
                    match=MatchValue(value=project_id),
                ),
                FieldCondition(
                    key="metadata.dataset_id",
                    match=MatchValue(value=dataset_id),
                ),
            ]
        ),
        limit=1,
    )

    if search_result[0]:
        existing_point = search_result[0][0]
        document_id = existing_point.id
        logger.info(
            f"Updating existing document with project_id={project_id}, "
            f"dataset_id={dataset_id}"
        )
    else:
        document_id = str(uuid4())
        logger.info(
            f"Adding new document with project_id={project_id}, "
            f"dataset_id={dataset_id}"
        )

    await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: vector_store.add_documents(
            documents=[document], ids=[document_id]
        ),
    )


def perform_similarity_search(
    vector_store,
    query,
    top_k=settings.QDRANT_TOP_K,
    query_filter=None,
):
    """
    Perform a similarity search.
    Filter the search based on provided query_filter.

    Args:
        vector_store: The vector store to search in
        query: The search query
        top_k: Number of results to return
        query_filter: Filter to apply to the search (Qdrant filter object)
    """

    try:
        return vector_store.similarity_search(
            query, k=top_k, filter=query_filter
        )
    except Exception as e:
        logger.error(
            f"Error performing similarity search: {e!s} | "
            f"Filter criteria: {query_filter}"
        )
        if query_filter:
            logger.info("Attempting unfiltered search as fallback...")
            return vector_store.similarity_search(query, k=top_k)
        else:
            raise e
