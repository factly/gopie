from langchain_core.documents import Document

from app.core.config import settings
from app.core.log import custom_logger as logger
from app.services.qdrant.qdrant_setup import QdrantSetup
from app.utils.model_registry.model_provider import get_model_provider


async def get_duckdb_docs(
    search_query: str,
    top_k: int = settings.QDRANT_DUCKDB_TOP_K,
) -> list[Document]:
    """
    Search DuckDB documentation for relevant information.

    Args:
        search_query: The query to search for (can be error message, user query, or SQL intent)
        top_k: Number of top results to return (default from settings)

    Returns:
        List of Document objects containing relevant DuckDB documentation snippets
    """
    try:
        embeddings = get_model_provider().get_embeddings_model()
        vector_store = QdrantSetup.get_vector_store(
            embeddings, collection_name=settings.QDRANT_DUCKDB_COLLECTION
        )

        results = await vector_store.asimilarity_search(
            search_query,
            k=top_k,
        )

        logger.info(
            f"DuckDB docs search returned {len(results)} results for query: '{search_query[:100]}...'"
        )

        return results

    except Exception as e:
        logger.exception(f"Error searching DuckDB documentation: {e!s}")
        return []


def format_duckdb_docs_context(docs: list[Document]) -> str:
    """
    Format DuckDB documentation snippets into a context string for LLM.

    Args:
        docs: List of Document objects from vector store search. Each Document's page_content field contains the full formatted documentation text.

    Returns:
        Formatted string containing the full documentation text from each Document's page_content field, presented as documentation snippets.
    """
    if not docs:
        return ""

    context_parts = ["## 📚 Relevant DuckDB Documentation\n"]

    for i, doc in enumerate(docs, 1):
        content = doc.page_content.strip()
        context_parts.append(f"### Documentation {i}\n```\n{content}\n```\n")

    return "\n".join(context_parts)
