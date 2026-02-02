from uuid import UUID, uuid5

from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import AsyncQdrantClient, QdrantClient, models

from app.core.config import settings

UUID_NAMESPACE = UUID("3896d314-1e95-4a3a-b45a-945f9f0b541d")


class QdrantSetup:
    """Singleton manager for Qdrant client connections and collection setup."""

    _async_client: AsyncQdrantClient | None = None
    _sync_client: QdrantClient | None = None
    _CONNECTION_TIMEOUT = 30

    @classmethod
    def get_document_id(cls, project_id: str, dataset_id: str) -> str:
        """Generate deterministic document ID from project and dataset IDs."""
        return str(uuid5(UUID_NAMESPACE, f"{project_id}_{dataset_id}"))

    @classmethod
    def _get_qdrant_url(cls) -> str:
        """Get Qdrant connection URL from settings."""
        return f"http://{settings.QDRANT_HOST}:{settings.QDRANT_PORT}"

    @classmethod
    async def get_async_client(cls, collection_name: str) -> AsyncQdrantClient:
        """
        Get or create async Qdrant client singleton.
        Creates collection if it doesn't exist.

        Args:
            collection_name: Name of the collection to ensure exists

        Returns:
            Initialized async Qdrant client
        """
        if cls._async_client is None:
            cls._async_client = AsyncQdrantClient(
                url=cls._get_qdrant_url(),
                check_compatibility=False,
                timeout=cls._CONNECTION_TIMEOUT,
            )

        if not await cls._async_collection_exists(cls._async_client, collection_name):
            config = cls.get_qdrant_config(collection_name)
            await cls._async_client.create_collection(**config)
        return cls._async_client

    @classmethod
    def get_sync_client(cls, collection_name: str) -> QdrantClient:
        """
        Get or create sync Qdrant client singleton.
        Creates collection if it doesn't exist.

        Args:
            collection_name: Name of the collection to ensure exists

        Returns:
            Initialized sync Qdrant client
        """
        if cls._sync_client is None:
            cls._sync_client = QdrantClient(
                url=cls._get_qdrant_url(),
                check_compatibility=False,
                timeout=cls._CONNECTION_TIMEOUT,
            )

        if not cls._collection_exists(cls._sync_client, collection_name):
            config = cls.get_qdrant_config(collection_name)
            cls._sync_client.create_collection(**config)
        return cls._sync_client

    @classmethod
    def get_qdrant_config(cls, collection_name: str) -> dict:
        return {
            "collection_name": collection_name,
            "vectors_config": {
                "dense": models.VectorParams(
                    size=settings.DEFAULT_EMBEDDING_SIZE,
                    distance=models.Distance.COSINE,
                    on_disk=True,
                ),
            },
            "sparse_vectors_config": {
                "sparse": models.SparseVectorParams(
                    index=models.SparseIndexParams(
                        on_disk=False,
                    ),
                ),
            },
            "hnsw_config": models.HnswConfigDiff(
                m=16,
                ef_construct=100,
                full_scan_threshold=20,
                max_indexing_threads=0,
                on_disk=False,
            ),
            "optimizers_config": models.OptimizersConfigDiff(
                deleted_threshold=0.2,
                vacuum_min_vector_number=1000,
                default_segment_number=0,
                max_segment_size=None,
                memmap_threshold=None,
                indexing_threshold=40,
                flush_interval_sec=5,
                max_optimization_threads=None,
            ),
            "wal_config": models.WalConfigDiff(wal_capacity_mb=32, wal_segments_ahead=0),
            "quantization_config": models.ScalarQuantization(
                scalar=models.ScalarQuantizationConfig(type=models.ScalarType.INT8, always_ram=True)
            ),
        }

    @classmethod
    def get_vector_store(
        cls, embeddings: OpenAIEmbeddings, collection_name: str
    ) -> QdrantVectorStore:
        client = cls.get_sync_client(collection_name)
        return QdrantVectorStore(
            client=client,
            collection_name=collection_name,
            embedding=embeddings,
        )

    @classmethod
    def _collection_exists(cls, client: QdrantClient, collection_name: str) -> bool:
        collections = client.get_collections().collections
        return any(col.name == collection_name for col in collections)

    @classmethod
    async def _async_collection_exists(
        cls, client: AsyncQdrantClient, collection_name: str
    ) -> bool:
        collections = (await client.get_collections()).collections
        return any(col.name == collection_name for col in collections)

    @classmethod
    async def close_clients(cls) -> None:
        if cls._sync_client:
            cls._sync_client.close()
            cls._sync_client = None
        if cls._async_client:
            await cls._async_client.close()
            cls._async_client = None
