from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from fastapi.templating import Jinja2Templates
from ....workflow.graph import stream_graph_updates

router = APIRouter()
templates = Jinja2Templates(directory="server/app/tests/templates")

@router.get("/")
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@router.get("/nl2sql")
async def get_nl2sql(user_input: str):
    """Stream the agent's processing events as Server-Sent Events."""
    return StreamingResponse(
        stream_graph_updates(user_input),
        media_type="text/event-stream",
    )
