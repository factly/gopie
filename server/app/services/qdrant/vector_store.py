"""Utilities for working with vector stores."""

from uuid import uuid4

from server.app.services.qdrant.csv_processing import process_csv_directory
from server.app.services.qdrant.qdrant_setup import (
    check_collection_has_documents,
    initialize_qdrant_client,
    setup_vector_store,
)
from server.app.core.config import settings
DATA_DIR = "./data"


def add_documents_to_vector_store(vector_store, documents, ids=None):
    """Add documents to the vector store."""
    if ids is None:
        ids = [str(uuid4()) for _ in range(len(documents))]
    vector_store.add_documents(documents=documents, ids=ids)


def perform_similarity_search(vector_store, query, top_k=settings.QDRANT_TOP_K):
    """Perform a similarity search."""
    return vector_store.similarity_search(query, k=top_k)


def vectorize_datasets(vector_store=None, directory_path: str = DATA_DIR):
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

    documents, ids = process_csv_directory(directory_path)

    if has_documents:
        print("Documents are already vectorized. Skipping vectorization.")
        return vector_store

    if documents:
        add_documents_to_vector_store(vector_store, documents, ids)
        print(f"Vectorized {len(documents)} dataset(s) from {directory_path}")
    else:
        print(f"No CSV files found in {directory_path}")

    return vector_store
