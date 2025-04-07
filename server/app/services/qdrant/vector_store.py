"""Utilities for working with vector stores."""

import logging
from typing import List, Optional
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
    dataset_ids: Optional[List[str]] = None,
):
    """
    Perform a similarity search.
    If dataset_ids are provided, filter the search to only include documents with matching dataset IDs.

    Args:
        vector_store: The vector store to search in
        query: The search query
        top_k: Number of results to return
        dataset_ids: Optional list of dataset IDs to filter results
    """
    filter_dict = None
    if dataset_ids:
        filter_dict = {
            "$or": [
                {"metadata.dataset_id": {"$eq": dataset_id}}
                for dataset_id in dataset_ids
            ]
        }
        logging.info(f"Filtering search to datasets: {dataset_ids}")

    try:
        return vector_store.similarity_search(query, k=top_k, filter=filter_dict)
    except Exception as e:
        logging.error(f"Error performing similarity search: {str(e)}")
        if filter_dict:
            logging.info("Attempting unfiltered search as fallback...")
            return vector_store.similarity_search(query, k=top_k)
        else:
            raise e
