from uuid import UUID, uuid5

from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import AsyncQdrantClient, QdrantClient
from qdrant_client.http.models import Distance, VectorParams

from app.core.config import settings

UUID_NAMESPACE = UUID("3896d314-1e95-4a3a-b45a-945f9f0b541d")


class QdrantSetup:
    async_client: AsyncQdrantClient | None = None
    sync_client: QdrantClient | None = None

    @classmethod
    def get_document_id(cls, project_id: str, dataset_id: str) -> str:
        return str(uuid5(UUID_NAMESPACE, f"{project_id}_{dataset_id}"))

    @classmethod
    async def get_async_client(cls) -> AsyncQdrantClient:
        if cls.async_client is None:
            cls.async_client = AsyncQdrantClient(
                url=f"http://{settings.QDRANT_HOST}:{settings.QDRANT_PORT}",
                check_compatibility=False,
            )

            if not await cls._async_collection_exists(cls.async_client):
                await cls.async_client.create_collection(
                    collection_name=settings.QDRANT_COLLECTION,
                    vectors_config=VectorParams(size=3072, distance=Distance.COSINE),
                )
        return cls.async_client

    @classmethod
    def get_sync_client(cls) -> QdrantClient:
        if cls.sync_client is None:
            cls.sync_client = QdrantClient(
                url=f"http://{settings.QDRANT_HOST}:{settings.QDRANT_PORT}",
                check_compatibility=False,
            )
            if not cls._collection_exists(cls.sync_client):
                cls.sync_client.create_collection(
                    collection_name=settings.QDRANT_COLLECTION,
                    vectors_config=VectorParams(size=3072, distance=Distance.COSINE),
                )
        return cls.sync_client

    @classmethod
    def get_vector_store(cls, embeddings: OpenAIEmbeddings) -> QdrantVectorStore:
        client = cls.get_sync_client()
        return QdrantVectorStore(
            client=client,
            collection_name=settings.QDRANT_COLLECTION,
            embedding=embeddings,
        )

    @classmethod
    def _collection_exists(cls, client: QdrantClient) -> bool:
        collections = client.get_collections().collections
        collection_names = [collection.name for collection in collections]
        return settings.QDRANT_COLLECTION in collection_names

    @classmethod
    async def _async_collection_exists(cls, client: AsyncQdrantClient) -> bool:
        collections = (await client.get_collections()).collections
        collection_names = [collection.name for collection in collections]
        return settings.QDRANT_COLLECTION in collection_names

    @classmethod
    async def close_clients(cls) -> None:
        if cls.sync_client:
            cls.sync_client.close()
            cls.sync_client = None
        if cls.async_client:
            await cls.async_client.close()
            cls.async_client = None
