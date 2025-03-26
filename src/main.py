import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.templating import Jinja2Templates

from src.lib.graph import stream_graph_updates
from src.utils.dataset_profiling import profile_all_datasets


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI application."""
    logging.info("Starting dataset pre-profiling...")
    try:
        data_dir = os.getenv("DATA_DIR", "./data")
        datasets = profile_all_datasets(data_dir=data_dir)
        logging.info(f"Successfully pre-profiled {len(datasets)} datasets")
    except Exception as e:
        logging.error(f"Error during dataset pre-profiling: {e}")

    yield

    logging.info("Shutting down application...")


app = FastAPI(lifespan=lifespan)
logging.basicConfig(filename="log/agent.log", level=logging.INFO)
# visualize_graph()

templates = Jinja2Templates(directory="src/test/templates")


@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse("stream_test.html", {"request": request})


@app.get("/nl2sql")
async def get_nl2sql(user_input: str):
    """Stream the agent's processing events as Server-Sent Events."""

    async def event_generator():
        async for chunk in stream_graph_updates(user_input):
            yield chunk

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
    )
