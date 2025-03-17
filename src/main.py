import logging

from fastapi import FastAPI
from fastapi.responses import StreamingResponse

from src.lib.graph import stream_graph_updates, visualize_graph

app = FastAPI()
logging.basicConfig(filename="log/agent.log", level=logging.INFO)
visualize_graph()


@app.get("/")
def read_root():
    return {"message": "Welcome to the Dataful Agent API"}


@app.get("/nl2sql")
async def get_nl2sql(user_input: str):
    return StreamingResponse(stream_graph_updates(user_input))
