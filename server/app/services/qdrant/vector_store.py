"""Utilities for working with vector stores."""

import logging
from uuid import uuid4

from app.core.config import settings
from app.services.qdrant.qdrant_setup import setup_vector_store


def add_documents_to_vector_store(documents, ids=None):
    """Add documents to the vector store."""
    vector_store = setup_vector_store()

    if ids is None:
        ids = [str(uuid4()) for _ in range(len(documents))]
    vector_store.add_documents(documents=documents, ids=ids)


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
