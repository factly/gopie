"""Utilities for working with vector stores."""

from uuid import uuid4

from src.utils.qdrant.csv_processing import process_csv_directory
from src.utils.qdrant.qdrant_setup import (
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


def perform_similarity_search(vector_store, query, top_k=1):
    """Perform a similarity search."""
    return vector_store.similarity_search(query, k=top_k)


def vectorize_datasets(
    vector_store=None, directory_path: str = DATA_DIR, force_vectorize: bool = False
):
    """
    Process and vectorize all datasets in the given directory.
    """
    client = None

    if vector_store is None:
        client = initialize_qdrant_client()
        vector_store = setup_vector_store(client)
    else:
        client = vector_store._client

    # Check if documents are already vectorized
    has_documents = check_collection_has_documents(client, "dataset_collection")

    if has_documents and not force_vectorize:
        print("Documents are already vectorized. Skipping vectorization.")
        return vector_store

    # Proceed with vectorization
    documents, ids = process_csv_directory(directory_path)
    if documents:
        add_documents_to_vector_store(vector_store, documents, ids)
        print(f"Vectorized {len(documents)} dataset(s) from {directory_path}")
    else:
        print(f"No CSV files found in {directory_path}")

    return vector_store


def force_revectorize_datasets(directory_path: str = DATA_DIR):
    """Force re-vectorization of all datasets in the directory."""
    client = initialize_qdrant_client()
    vector_store = setup_vector_store(client)

    # Force re-vectorization
    return vectorize_datasets(vector_store, directory_path, force_vectorize=True)
