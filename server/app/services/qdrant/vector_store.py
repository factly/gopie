import logging
from uuid import uuid4
import asyncio

from app.core.config import settings
from app.services.qdrant.qdrant_setup import setup_vector_store
from app.core.langchain_config import lc

async def add_documents_to_vector_store(documents, ids=None):
    vector_store = setup_vector_store(lc.embeddings_model)

    if ids is None:
        ids = [str(uuid4()) for _ in range(len(documents))]

    await asyncio.get_event_loop().run_in_executor(
        None, lambda: vector_store.add_documents(documents=documents, ids=ids)
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
        return vector_store.similarity_search(query, k=top_k, filter=query_filter)
    except Exception as e:
        logging.error(
            f"Error performing similarity search: {str(e)} | Filter criteria: {query_filter}"
        )
        if query_filter:
            logging.info("Attempting unfiltered search as fallback...")
            return vector_store.similarity_search(query, k=top_k)
        else:
            raise e
