import json

from langchain_openai import OpenAIEmbeddings
from qdrant_client import models

from app.core.config import settings
from app.core.log import logger
from app.models.schema import DatasetSchema
from app.services.qdrant.vector_store import (
    perform_similarity_search,
    setup_vector_store,
)


async def search_schemas(
    user_query: str,
    embeddings: OpenAIEmbeddings,
    project_ids: list[str] | None = None,
    dataset_ids: list[str] | None = None,
    top_k: int = settings.QDRANT_TOP_K,
) -> list[DatasetSchema]:
    """
    Search for schemas using a vector search.

    Returns:
        List of matching dataset schemas
    """
    try:
        vector_store = setup_vector_store(embeddings=embeddings)
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
            formatted_schema = json.loads(doc.page_content)
            schemas.append(formatted_schema)

        logger.debug(
            f"Found {len(schemas)} schemas matching query: {user_query}"
        )
        return schemas

    except Exception as e:
        logger.error(f"Error searching schemas: {e!s}")
        return []
