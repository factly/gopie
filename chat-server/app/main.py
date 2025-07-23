import time

import uvicorn
from fastapi import FastAPI, Request
from fastapi.concurrency import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.routers.dataset_upload import (
    dataset_router as schema_upload_router,
)
from app.api.v1.routers.query import router as query_router
from app.core.config import settings
from app.core.log import logger, setup_logger
from app.core.session import SingletonAiohttp
from app.services.qdrant.qdrant_setup import QdrantSetup
from app.utils.graph_utils.generate_graph import visualize_graph


@asynccontextmanager
async def lifespan(app: FastAPI):
    SingletonAiohttp.get_aiohttp_client()
    await QdrantSetup.get_async_client()
    QdrantSetup.get_sync_client()
    try:
        setup_logger()
        visualize_graph()
    except Exception as e:
        logger.error(f"Failed to generate graph visualization: {e}")
    yield
    await QdrantSetup.close_clients()
    await SingletonAiohttp.close_aiohttp_client()


app = FastAPI(
    title=settings.PROJECT_NAME,
    docs_url="/api/docs",
    openapi_url="/api",
    lifespan=lifespan,
)


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=settings.CORS_ORIGINS,
    allow_methods=settings.CORS_METHODS,
    allow_headers=settings.CORS_HEADERS,
)

app.include_router(query_router, prefix=settings.API_V1_STR, tags=["query"])
app.include_router(schema_upload_router, prefix=settings.API_V1_STR, tags=["upload_schema"])


def start():
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info",
    )
