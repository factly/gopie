import asyncio
import logging
from uuid import uuid4

from app.core.config import settings
from app.core.langchain_config import lc
from app.services.qdrant.qdrant_setup import (
    initialize_qdrant_client,
    setup_vector_store,
)
from qdrant_client.http.models import FieldCondition, Filter, MatchValue


async def add_documents_to_vector_store(documents, ids=None):
    vector_store = setup_vector_store(lc.embeddings_model)
    client = initialize_qdrant_client()

    if ids is None:
        ids = [str(uuid4()) for _ in range(len(documents))]

    filtered_docs = []
    filtered_ids = []

    for doc, doc_id in zip(documents, ids):
        project_id = doc.metadata["project_id"]
        dataset_id = doc.metadata["dataset_id"]
        file_path = doc.metadata["file_path"]

        search_result = client.scroll(
            collection_name=settings.QDRANT_COLLECTION,
            scroll_filter=Filter(
                must=[
                    FieldCondition(
                        key="metadata.project_id",
                        match=MatchValue(value=project_id),
                    ),
                    FieldCondition(
                        key="metadata.dataset_id",
                        match=MatchValue(value=dataset_id),
                    ),
                    FieldCondition(
                        key="metadata.file_path",
                        match=MatchValue(value=file_path),
                    ),
                ]
            ),
            limit=1,
        )

        if search_result[0]:
            logging.info(
                f"Document with project_id={project_id}, dataset_id={dataset_id}, file_path={file_path} already exists in Qdrant. Skipping."
            )
            continue

        filtered_docs.append(doc)
        filtered_ids.append(doc_id)

    if filtered_docs:
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: vector_store.add_documents(
                documents=filtered_docs, ids=filtered_ids
            ),
        )


def perform_similarity_search(
    vector_store,
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
        return vector_store.similarity_search(query, k=top_k, filter=query_filter)
    except Exception as e:
        logging.error(
            f"Error performing similarity search: {str(e)} | Filter criteria: {query_filter}"
        )
        if query_filter:
            logging.info("Attempting unfiltered search as fallback...")
            return vector_store.similarity_search(query, k=top_k)
        else:
            raise e
