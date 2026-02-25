from fastembed import SparseTextEmbedding
from langchain_core.documents import Document
from qdrant_client import models

from app.core.config import settings
from app.core.log import custom_logger as logger
from app.services.qdrant.qdrant_setup import QdrantSetup
from app.utils.model_registry.model_provider import get_model_provider


class SparseModelManager:
    """
    Singleton manager for sparse text embedding model.
    """

    _model: SparseTextEmbedding | None = None

    @classmethod
    def get_model(cls) -> SparseTextEmbedding:
        """
        Get or initialize the sparse text embedding model.
        Uses SPLADE for better keyword matching with learned term importance.
        """
        if cls._model is None:
            logger.info(f"Initializing sparse model: {settings.DEFAULT_SPARSE_MODEL}")
            cls._model = SparseTextEmbedding(model_name=settings.DEFAULT_SPARSE_MODEL)
            logger.info("Sparse model initialization complete")
        return cls._model


def generate_sparse_vector(text: str) -> models.SparseVector:
    """
    Generate sparse vector using SPLADE for keyword matching.

    SPLADE (Sparse Lexical and Expansion) provides:
    - Learned term importance (not just TF)
    - Query/document expansion (e.g., "car" matches "vehicle", "automobile")
    - Better than simple BM25 for semantic keyword matching
    - Proper vocabulary indices (no hash collisions)

    Args:
        text: Text to generate sparse vector from

    Returns:
        SparseVector with indices (vocabulary IDs) and values (learned weights)
    """
    sparse_model = SparseModelManager.get_model()
    result = list(sparse_model.embed([text]))[0]
    return models.SparseVector(indices=result.indices.tolist(), values=result.values.tolist())


async def add_document_to_vector_store(document: Document):
    """
    Add document to Qdrant with both dense and sparse vectors for hybrid search.

    Dense vector: OpenAI embedding of page_content
    Sparse vector: SPLADE embedding of dataset_name + name + description
    """
    project_id = document.metadata["project_id"]
    dataset_id = document.metadata["dataset_id"]
    document_id = QdrantSetup.get_document_id(project_id, dataset_id)

    # Generate dense vector (OpenAI embedding)
    embeddings_model = get_model_provider().get_embeddings_model()
    dense_vector = embeddings_model.embed_query(document.page_content)

    dataset_name = document.metadata.get("dataset_name", "")
    name = document.metadata.get("name", "")
    description = document.metadata.get("dataset_description", "")
    sparse_text = f"{dataset_name} {name} {description}"
    sparse_vector = generate_sparse_vector(sparse_text)

    # Get Qdrant client and upload point with both vectors
    client = await QdrantSetup.get_async_client(settings.QDRANT_COLLECTION)

    point = models.PointStruct(
        id=document_id,
        vector={
            "dense": dense_vector,
            "sparse": sparse_vector,
        },
        payload={
            "page_content": document.page_content,
            "metadata": document.metadata,
        },
    )

    await client.upsert(
        collection_name=settings.QDRANT_COLLECTION,
        points=[point],
    )
