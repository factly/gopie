import logging

from fastapi import FastAPI
from fastapi.responses import StreamingResponse

from src.lib.graph import stream_graph_updates
from src.utils.qdrant.dataset_search import find_and_preview_dataset

app = FastAPI()
logging.basicConfig(filename="log/agent.log", level=logging.INFO)
find_and_preview_dataset("How much CSR amount was spent in the year 2018?")


@app.get("/")
def read_root():
    return {"message": "Welcome to the Dataful Agent API"}


@app.get("/nl2sql")
async def get_nl2sql(user_input: str):
    return StreamingResponse(stream_graph_updates(user_input))
