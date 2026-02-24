import asyncio
from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from qdrant_client import AsyncQdrantClient

from app.core.config import settings
from app.core.log import logger

router = APIRouter()


async def check_qdrant_health() -> Dict[str, Any]:
    """
    Check Qdrant vector database connectivity and required collection exists.
    """

    try:
        client = AsyncQdrantClient(
            url=f"http://{settings.QDRANT_HOST}:{settings.QDRANT_PORT}",
            check_compatibility=False,
        )

        # Test basic connectivity by getting collections
        collections = await client.get_collections()
        collection_names = [collection.name for collection in collections.collections]

        await client.close()

        # Check if the required collection exists
        required_collection = settings.QDRANT_COLLECTION
        collection_exists = required_collection in collection_names

        if collection_exists:
            return {
                "status": "healthy",
                "collections_count": len(collections.collections),
                "required_collection": required_collection,
                "collection_exists": True,
            }
        else:
            return {
                "status": "unhealthy",
                "error": f"Required collection '{required_collection}' not found",
                "collections_count": len(collections.collections),
                "available_collections": collection_names,
                "required_collection": required_collection,
                "collection_exists": False,
            }
    except Exception as e:
        logger.exception("Error checking Qdrant health: %s", e)
        return {"status": "unhealthy", "error": str(e), "collection_exists": False}


async def check_llm_provider_health() -> Dict[str, Any]:
    """
    Check if LLM provider can be properly instantiated.
    """

    if not settings.LLM_GATEWAY_PROVIDER:
        return {"status": "not_configured", "error": "LLM_GATEWAY_PROVIDER not configured"}

    try:
        from app.utils.model_registry.model_provider import get_llm_provider

        # Test provider instantiation with sample metadata
        metadata = {"session_id": "health_check", "user_id": "system"}
        provider = get_llm_provider(metadata)

        # Test getting an LLM model if default model is configured
        if settings.DEFAULT_LLM_MODEL:
            _ = provider.get_llm_model(settings.DEFAULT_LLM_MODEL)
            return {
                "status": "healthy",
                "provider_type": settings.LLM_GATEWAY_PROVIDER,
                "default_model": settings.DEFAULT_LLM_MODEL,
                "model_created": True,
            }
        else:
            return {
                "status": "healthy",
                "provider_type": settings.LLM_GATEWAY_PROVIDER,
                "default_model": None,
                "model_created": False,
                "note": "Provider instantiated but no default model configured",
            }
    except Exception as e:
        logger.exception("Error checking LLM provider health: %s", e)
        return {
            "status": "unhealthy",
            "provider_type": settings.LLM_GATEWAY_PROVIDER,
            "error": str(e),
        }


async def check_gopie_server_health() -> Dict[str, Any]:
    """
    Check Gopie server connectivity.
    """

    if not settings.GOPIE_API_ENDPOINT:
        return {"status": "not_configured", "error": "GOPIE_API_ENDPOINT not configured"}

    try:
        from app.services.gopie.client import GopieClient

        client = GopieClient(org_id="health_check", user_id="system")
        # Test basic connectivity to Gopie server
        async with await client.get("/") as response:
            # Any response (even 404) means the server is reachable
            return {"status": "healthy", "response_code": response.status, "server_reachable": True}
    except Exception as e:
        logger.exception("Error checking Gopie server health: %s", e)
        return {"status": "unhealthy", "error": str(e), "server_reachable": False}


async def check_embedding_provider_health() -> Dict[str, Any]:
    """
    Check if embedding provider can be properly instantiated.
    """

    if not settings.EMBEDDING_GATEWAY_PROVIDER:
        return {"status": "not_configured", "error": "EMBEDDING_GATEWAY_PROVIDER not configured"}

    try:
        from app.utils.model_registry.model_provider import (
            get_embedding_provider,
        )

        # Test provider instantiation with sample metadata
        metadata = {"session_id": "health_check", "user_id": "system"}
        provider = get_embedding_provider(metadata)

        # Test getting an embedding model if default model is configured
        if settings.DEFAULT_EMBEDDING_MODEL:
            embedding_model = provider.get_embeddings_model(settings.DEFAULT_EMBEDDING_MODEL)
            _ = await embedding_model.aembed_query("test")
            return {
                "status": "healthy",
                "provider_type": settings.EMBEDDING_GATEWAY_PROVIDER,
                "default_model": settings.DEFAULT_EMBEDDING_MODEL,
                "model_created": True,
            }
        else:
            return {
                "status": "healthy",
                "provider_type": settings.EMBEDDING_GATEWAY_PROVIDER,
                "default_model": None,
                "model_created": False,
                "note": "Provider instantiated but no default model configured",
            }
    except Exception as e:
        logger.exception("Error checking embedding provider health: %s", e)
        return {
            "status": "unhealthy",
            "provider_type": settings.EMBEDDING_GATEWAY_PROVIDER,
            "error": str(e),
        }


async def check_sparse_model_health() -> Dict[str, Any]:
    """
    Check if sparse model can be properly instantiated and generate vectors.
    """
    try:
        from app.services.qdrant.vector_store import generate_sparse_vector

        # Test vector generation
        # Run in executor to avoid blocking event loop since it is CPU intensive
        loop = asyncio.get_running_loop()
        vector = await loop.run_in_executor(None, generate_sparse_vector, "test")

        if vector and vector.indices:
            return {
                "status": "healthy",
                "model_loaded": True,
                "vector_generated": True,
            }
        else:
            return {
                "status": "unhealthy",
                "error": "Generated vector is empty",
                "model_loaded": True,
            }

    except Exception as e:
        logger.exception("Error checking sparse model health: %s", e)
        return {
            "status": "unhealthy",
            "error": str(e),
        }


@router.get("/health")
async def health_check():
    """
    Comprehensive health check endpoint that verifies connectivity to all dependent services.

    Checks:
    - Qdrant vector database
    - LLM provider instantiation
    - Gopie server
    - Embedding provider instantiation
    - Sparse model instantiation
    """
    start_time = datetime.now()

    qdrant_task = asyncio.create_task(check_qdrant_health())
    llm_task = asyncio.create_task(check_llm_provider_health())
    gopie_task = asyncio.create_task(check_gopie_server_health())
    embedding_task = asyncio.create_task(check_embedding_provider_health())
    sparse_model_task = asyncio.create_task(check_sparse_model_health())

    (
        qdrant_health,
        llm_health,
        gopie_health,
        embedding_health,
        sparse_model_health,
    ) = await asyncio.gather(
        qdrant_task,
        llm_task,
        gopie_task,
        embedding_task,
        sparse_model_task,
        return_exceptions=True,
    )

    def safe_result(result, service_name):
        if isinstance(result, BaseException):
            return {
                "status": "error",
                "error": f"Health check failed: {service_name} - {str(result)}",
            }
        return result

    qdrant_health = safe_result(qdrant_health, "qdrant")
    llm_health = safe_result(llm_health, "llm")
    gopie_health = safe_result(gopie_health, "gopie")
    embedding_health = safe_result(embedding_health, "embedding")
    sparse_model_health = safe_result(sparse_model_health, "sparse_model")

    all_services = [
        qdrant_health,
        llm_health,
        gopie_health,
        embedding_health,
        sparse_model_health,
    ]
    unhealthy_services = [
        service
        for service in all_services
        if service.get("status") not in ["healthy", "not_configured"]
    ]

    overall_status = "healthy" if not unhealthy_services else "unhealthy"

    end_time = datetime.now()
    total_check_time = (end_time - start_time).total_seconds() * 1000

    response_data = {
        "status": overall_status,
        "timestamp": end_time.isoformat(),
        "service": "gopie-chat-server",
        "total_check_time_ms": round(total_check_time, 2),
        "services": {
            "qdrant": qdrant_health,
            "llm_provider": llm_health,
            "gopie_server": gopie_health,
            "embedding_provider": embedding_health,
            "sparse_model": sparse_model_health,
        },
    }

    status_code = (
        200 if overall_status == "healthy" else 503 if overall_status == "unhealthy" else 200
    )

    return JSONResponse(status_code=status_code, content=response_data)
