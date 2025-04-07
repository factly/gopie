import logging
from typing import List, Optional

from app.core.config import settings
from app.models.schema import DatasetSchema
from app.services.qdrant.vector_store import (
    perform_similarity_search,
    setup_vector_store,
)


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

        # If project_id is provided and dataset_ids is not, get all datasets for the project
        if project_ids and not dataset_ids:
            # For now, we'll proceed with the search without dataset filtering
            pass

        results = perform_similarity_search(
            vector_store=vector_store,
            query=user_query,
            top_k=top_k,
            dataset_ids=dataset_ids,
        )

        schemas = []
        for doc in results:
            if "schema" in doc.metadata:
                schemas.append(doc.metadata["schema"])

        logging.info(f"Found {len(schemas)} schemas matching query: {user_query}")
        return schemas

    except Exception as e:
        logging.error(f"Error searching schemas: {str(e)}")
        return []
