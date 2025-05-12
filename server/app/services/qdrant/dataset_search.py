import logging

from langchain_openai import OpenAIEmbeddings
from qdrant_client import models

from app.core.config import settings
from app.models.schema import DatasetSchema
from app.services.gopie.dataset_info import format_schema
from app.services.gopie.generate_schema import generate_schema
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
            fetched_schema, sample_data = await generate_schema(
                doc.metadata["dataset_name"]
            )

            formatted_schema = format_schema(
                fetched_schema,
                sample_data,
                doc.metadata["project_id"],
                doc.metadata["dataset_id"],
            )
            formatted_schema["name"] = doc.metadata["name"]
            formatted_schema["dataset_name"] = doc.metadata["dataset_name"]
            formatted_schema["dataset_description"] = doc.metadata[
                "dataset_description"
            ]

            schemas.append(formatted_schema)

        logging.info(
            f"Found {len(schemas)} schemas matching query: {user_query}"
        )
        return schemas

    except Exception as e:
        logging.error(f"Error searching schemas: {e!s}")
        return []
