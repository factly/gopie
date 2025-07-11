from langchain_core.documents import Document
from langchain_core.vectorstores.base import VectorStore

from app.core.config import settings
from app.core.log import logger
from app.services.qdrant.qdrant_setup import QdrantSetup
from app.utils.model_registry.model_provider import get_model_provider


async def add_document_to_vector_store(document: Document):
    vector_store = QdrantSetup.get_vector_store(get_model_provider().get_embeddings_model())
    project_id = document.metadata["project_id"]
    dataset_id = document.metadata["dataset_id"]
    document_id = QdrantSetup.get_document_id(project_id, dataset_id)
    await vector_store.aadd_documents(documents=[document], ids=[document_id])


async def perform_similarity_search(
    vector_store: VectorStore,
    query,
    top_k=settings.QDRANT_TOP_K,
    query_filter=None,
):
    """
    Perform a similarity search.
    Filter the search based on provided query_filter.

    Args:
        vector_store: The vector store to search in
        query: The search query
        top_k: Number of results to return
        query_filter: Filter to apply to the search (Qdrant filter object)
    """

    try:
        return await vector_store.asimilarity_search(query, k=top_k, filter=query_filter)
    except Exception as e:
        logger.error(
            f"Error performing similarity search: {e!s} | " f"Filter criteria: {query_filter}"
        )
        if query_filter:
            logger.info("Attempting unfiltered search as fallback...")
            return await vector_store.asimilarity_search(query, k=top_k)
        else:
            raise e
