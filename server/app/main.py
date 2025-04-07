import logging
import os
import sys
import time

import uvicorn
from app.api.v1.routers.dataset_upload import dataset_router as schema_upload_router
from app.api.v1.routers.qdrant import router as qdrant_router
from app.api.v1.routers.query import router as query_router
from app.core.config import settings
from app.core.session import SingletonAiohttp
from fastapi import FastAPI, Request
from fastapi.concurrency import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    SingletonAiohttp.get_aiohttp_client()
    yield
    await SingletonAiohttp.close_aiohttp_client()


app = FastAPI(
    title=settings.PROJECT_NAME,
    docs_url="/api/docs",
    openapi_url="/api",
    lifespan=lifespan,
)
if settings.MODE == "development":
    os.makedirs(settings.LOG_DIR, exist_ok=True)
    logging.basicConfig(
        filename=os.path.join(settings.LOG_DIR, "agent.log"),
        level=logging.INFO,
        handlers=[logging.StreamHandler(sys.stdout)],
    )
else:
    logging.basicConfig(level=logging.INFO)


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
app.include_router(
    schema_upload_router, prefix=settings.API_V1_STR, tags=["upload_schema"]
)
app.include_router(
    qdrant_router, prefix=settings.API_V1_STR + "/qdrant", tags=["qdrant"]
)


def start():
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
