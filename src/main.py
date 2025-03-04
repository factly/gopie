import logging
from stat import filemode
from fastapi import FastAPI
from src.lib.graph import stream_graph_updates, visualize_graph
from fastapi.responses import StreamingResponse

app = FastAPI()
logging.basicConfig(filename="log/agent.log", level=logging.INFO)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Dataful Agent API"}

@app.get("/nl2sql")
async def get_nl2sql(user_input: str):
    visualize_graph()
    return StreamingResponse(stream_graph_updates(user_input))
