"""Utilities for working with vector stores."""

import logging
from typing import List, Optional
from uuid import uuid4

from app.core.config import settings
from app.services.qdrant.csv_processing import process_csv_directory
from app.services.qdrant.qdrant_setup import (
    check_collection_has_documents,
    initialize_qdrant_client,
    setup_vector_store,
)

DATA_DIR = "./data"


def add_documents_to_vector_store(vector_store, documents, ids=None):
    """Add documents to the vector store."""
    if ids is None:
        ids = [str(uuid4()) for _ in range(len(documents))]
    vector_store.add_documents(documents=documents, ids=ids)


def perform_similarity_search(
    vector_store,
    query,
    top_k=settings.QDRANT_TOP_K,
    dataset_ids: Optional[List[str]] = None
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
    filter_by_dataset = None
    if dataset_ids:
        filter_by_dataset = {
            "filter": {
                "$or": [
                    {"file_name": {"$eq": f"{dataset_id}.csv"}}
                    for dataset_id in dataset_ids
                ]
            }
        }
        logging.info(f"Filtering search to datasets: {dataset_ids}")

    return vector_store.similarity_search(query, k=top_k, filter=filter_by_dataset)


def vectorize_datasets(vector_store=None):
    """
    Process and vectorize all datasets in the given directory.
    """
    client = None

    if vector_store is None:
        client = initialize_qdrant_client()
        vector_store = setup_vector_store(client)
    else:
        client = vector_store._client

    has_documents = check_collection_has_documents(client, "dataset_collection")
    documents, ids = process_csv_directory()

    if has_documents:
        logging.info("Documents are already vectorized. Skipping vectorization.")
        return vector_store

    if documents:
        add_documents_to_vector_store(vector_store, documents, ids)
        logging.info(f"Vectorized {len(documents)} dataset(s) from {DATA_DIR}")
    else:
        logging.warning(f"No CSV files found in {DATA_DIR}")

    return vector_store
