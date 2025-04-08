import logging
from typing import List, Optional

from app.core.config import settings
from app.models.schema import DatasetSchema
from app.services.qdrant.vector_store import (
    perform_similarity_search,
    setup_vector_store,
)
from qdrant_client import models


def search_schemas(
    user_query: str,
    project_ids: Optional[List[str]] = None,
    dataset_ids: Optional[List[str]] = None,
    top_k: int = settings.QDRANT_TOP_K,
) -> List[DatasetSchema]:
    """
    Search for schemas using a vector search.

    Args:
        query: The search query
        project_id: Optional project ID to filter results
        dataset_ids: Optional list of dataset IDs to filter results
        top_k: Number of results to return

    Returns:
        List of matching dataset schemas
    """
    try:
        vector_store = setup_vector_store()
        query_filter = None

        filter_conditions = []

        if project_ids:
            filter_conditions.append(
                models.FieldCondition(
                    key="metadata.project_id",
                    match=models.MatchAny(any=project_ids),
                )
            )

        if dataset_ids:
            filter_conditions.append(
                models.FieldCondition(
                    key="metadata.dataset_id",
                    match=models.MatchAny(any=dataset_ids),
                )
            )

        if filter_conditions:
            query_filter = models.Filter(should=filter_conditions)

        results = perform_similarity_search(
            vector_store=vector_store,
            query=user_query,
            top_k=top_k,
            query_filter=query_filter,
        )

        schemas = []
        for doc in results:
            schemas.append(doc.metadata)

        logging.info(f"Found {len(schemas)} schemas matching query: {user_query}")
        return schemas

    except Exception as e:
        logging.error(f"Error searching schemas: {str(e)}")
        return []
