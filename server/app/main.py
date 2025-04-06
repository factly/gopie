import logging
import os
import time

import uvicorn
from fastapi import FastAPI, Request
from fastapi.concurrency import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware

from server.app.api.v1.routers.dataset_upload import (
    dataset_router as schema_upload_router,
)
from server.app.api.v1.routers.query import router as query_router
from server.app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        logging.info("Starting the application...")
    except Exception as e:
        logging.error(f"Error starting the application: {e}")
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    docs_url="/api/docs",
    openapi_url="/api",
    lifespan=lifespan,
)
logging.basicConfig(
    level=logging.INFO,
    handlers=[
        logging.FileHandler(os.path.join(settings.LOG_DIR, "agent.log")),
        logging.StreamHandler(),
    ],
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
app.include_router(
    schema_upload_router, prefix=settings.API_V1_STR, tags=["upload_schema"]
)


def start():
    os.makedirs(settings.LOG_DIR, exist_ok=True)
    uvicorn.run("server.app.main:app", host="0.0.0.0", port=8090, reload=True)
