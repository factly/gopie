from langchain_openai import OpenAIEmbeddings
from langsmith import traceable
from qdrant_client import models

from app.core.config import settings
from app.core.log import custom_logger as logger
from app.models.schema import DatasetSchema
from app.services.qdrant.qdrant_setup import QdrantSetup
from app.services.qdrant.vector_store import generate_sparse_vector


def _build_qdrant_filter(
    project_ids: list[str] | None,
    dataset_ids: list[str] | None,
    org_id: str | None,
) -> models.Filter | None:
    """
    Build a Qdrant filter from project_ids, dataset_ids and org_id.

    Semantics:
    - org_id: MUST match (security boundary for multi-tenant isolation)
    - project_ids OR dataset_ids: SHOULD match (within the org scope)
    """
    must_conditions: list[models.Condition] = []
    should_conditions: list[models.Condition] = []

    if org_id:
        must_conditions.append(
            models.FieldCondition(
                key="metadata.org_id",
                match=models.MatchValue(value=org_id),
            )
        )
        logger.debug(f"Applied org_id filter: {org_id}")

    if project_ids:
        should_conditions.append(
            models.FieldCondition(
                key="metadata.project_id",
                match=models.MatchAny(any=project_ids),
            )
        )

    if dataset_ids:
        should_conditions.append(
            models.FieldCondition(
                key="metadata.dataset_id",
                match=models.MatchAny(any=dataset_ids),
            )
        )

    if not must_conditions and not should_conditions:
        return None

    if should_conditions and not must_conditions:
        logger.warning("No org_id filter applied - ensure this is intentional")

    filter_kwargs = {}
    if must_conditions:
        filter_kwargs["must"] = must_conditions
    if should_conditions:
        filter_kwargs["should"] = should_conditions

    return models.Filter(**filter_kwargs)


@traceable(run_type="tool", name="search_schemas")
async def search_schemas(
    user_query: str,
    embeddings: OpenAIEmbeddings,
    project_ids: list[str] | None = None,
    dataset_ids: list[str] | None = None,
    org_id: str | None = None,
    top_k: int = settings.QDRANT_TOP_K,
) -> list[DatasetSchema]:
    """
    Hybrid search: dense (semantic) + sparse (keyword) with RRF fusion.

    The sparse vectors automatically handle exact keyword matching for dataset names.
    No extraction logic needed - if user mentions "st32_5ec", it matches via sparse vector.

    Returns:
        List of matching dataset schemas, ranked by hybrid score
    """
    try:
        dense_vector = embeddings.embed_query(user_query)
        sparse_vector = generate_sparse_vector(user_query)

        query_filter = _build_qdrant_filter(
            project_ids=project_ids,
            dataset_ids=dataset_ids,
            org_id=org_id,
        )

        client = await QdrantSetup.get_async_client(settings.QDRANT_COLLECTION)

        # Hybrid query with prefetch + RRF fusion
        query_response = await client.query_points(
            collection_name=settings.QDRANT_COLLECTION,
            prefetch=[
                # Dense: semantic similarity
                models.Prefetch(
                    query=dense_vector,
                    using="dense",
                    limit=20,
                    filter=query_filter,
                ),
                # Sparse: keyword matching
                models.Prefetch(
                    query=sparse_vector,
                    using="sparse",
                    limit=20,
                    filter=query_filter,
                ),
            ],
            # Reciprocal Rank Fusion combines both signals
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=top_k,
        )

        points = query_response.points

        schemas: list[DatasetSchema] = []
        for point in points:
            payload = point.payload or {}
            metadata = payload.get("metadata", {})
            schemas.append(DatasetSchema(**metadata))

        logger.debug(f"Hybrid search found {len(schemas)} schemas for query: {user_query}")
        return schemas

    except Exception as e:
        logger.exception(f"Error in hybrid schema search: {e!s}")
        return []
