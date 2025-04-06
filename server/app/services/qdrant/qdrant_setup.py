import logging

from app.core.config import settings
from app.core.langchain_config import lc
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.http.models import CountResult, Distance, Filter, VectorParams


def initialize_qdrant_client():
    """Initialize the Qdrant client and create a collection if it doesn't exist."""
    client = QdrantClient(url=f"http://{settings.QDRANT_HOST}:{settings.QDRANT_PORT}")

    if not collection_exists(client):
        client.create_collection(
            collection_name=settings.QDRANT_COLLECTION,
            vectors_config=VectorParams(size=3072, distance=Distance.COSINE),
        )
    return client


def setup_vector_store(client):
    """Set up a vector store using the provided client."""
    return QdrantVectorStore(
        client=client,
        collection_name=settings.QDRANT_COLLECTION,
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
        logging.info(f"Error checking if collection has documents: {e}")
        return False


def collection_exists(client) -> bool:
    """Check if the collection exists."""
    collections = client.get_collections().collections
    collection_names = [collection.name for collection in collections]
    return settings.QDRANT_COLLECTION in collection_names
