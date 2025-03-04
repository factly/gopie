from fastapi import FastAPI
from src.lib.graph import stream_graph_updates

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Welcome to the Dataful Agent API"}

@app.get("/nl2sql")
async def get_nl2sql(user_input: str):
    output = stream_graph_updates(user_input)
    return output