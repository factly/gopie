import logging
import os
import time
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from server.app.core.config import settings
from server.app.services.dataset_profiling import profile_all_datasets
from server.app.api.api_v1.routers.nl2sql import router as nl2sql_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        data_dir = settings.DATA_DIR
        datasets = profile_all_datasets(data_dir=data_dir)
    except Exception as e:
        logging.error(f"Error during dataset profiling: {e}")

    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    docs_url="/api/docs",
    openapi_url="/api",
    lifespan=lifespan,
)
logging.basicConfig(filename=os.path.join(settings.LOG_DIR, "agent.log"), level=logging.INFO)

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_methods=settings.CORS_METHODS,
    allow_headers=settings.CORS_HEADERS,
)

app.include_router(nl2sql_router, prefix=settings.API_V1_STR, tags=["nl2sql"])

def start():
    os.makedirs(settings.LOG_DIR, exist_ok=True)
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)