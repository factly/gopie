from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

from app.core.config import settings


def initialize_qdrant_client():
    if settings.MODE == "development":
        client = QdrantClient(":memory:")
    else:
        client = QdrantClient(
            url=f"https://{settings.QDRANT_HOST}:{settings.QDRANT_PORT}",
            check_compatibility=False,
        )
    
    if not collection_exists(client):
        client.create_collection(
            collection_name=settings.QDRANT_COLLECTION,
            vectors_config=VectorParams(size=3072, distance=Distance.COSINE),
        )
    return client


def setup_vector_store(embeddings: OpenAIEmbeddings):
    client = initialize_qdrant_client()
    return QdrantVectorStore(
        client=client,
        collection_name=settings.QDRANT_COLLECTION,
        embedding=embeddings,
    )


def collection_exists(client) -> bool:
    collections = client.get_collections().collections
    collection_names = [collection.name for collection in collections]
    return settings.QDRANT_COLLECTION in collection_names
