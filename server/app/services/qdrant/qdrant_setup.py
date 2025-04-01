"""Utilities for setting up Qdrant client and vector store."""

from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.http.models import CountResult, Distance, Filter, VectorParams

from server.app.core.langchain_config import lc
from server.app.core.config import settings

def initialize_qdrant_client():
    """Initialize the Qdrant client and create a collection if it doesn't exist."""
    client = QdrantClient(url=f"http://{settings.QDRANT_HOST}:{settings.QDRANT_PORT}")

    if not collection_exists(client, "dataset_collection"):
        client.create_collection(
            collection_name="dataset_collection",
            vectors_config=VectorParams(size=3072, distance=Distance.COSINE),
        )
    return client


def setup_vector_store(client, collection_name="dataset_collection"):
    """Set up a vector store using the provided client."""
    return QdrantVectorStore(
        client=client,
        collection_name=collection_name,
        embedding=lc.embeddings_model,
    )


def check_collection_has_documents(
    client, collection_name="dataset_collection"
) -> bool:
    """Check if the collection has documents."""
    try:
        count_result: CountResult = client.count(
            collection_name=collection_name,
            count_filter=Filter(must=[]),
        )
        return count_result.count > 0
    except Exception as e:
        print(f"Error checking if collection has documents: {e}")
        return False


def collection_exists(client, collection_name="dataset_collection") -> bool:
    """Check if the collection exists."""
    collections = client.get_collections().collections
    collection_names = [collection.name for collection in collections]
    return collection_name in collection_names
