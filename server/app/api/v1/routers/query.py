from typing import Optional
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from fastapi.templating import Jinja2Templates
from app.workflow.graph import stream_graph_updates


router = APIRouter()
templates = Jinja2Templates(directory="server/app/tests/templates")

@router.get("/")
async def root(request: Request):
    return templates.TemplateResponse("stream_test.html", {"request": request})


@router.get("/query")
async def get_nl2sql(user_input: str, dataset_id: Optional[str] = None):
    """Stream the agent's processing events as Server-Sent Events.

    Args:
        user_input: The natural language query from the user
        dataset_id: Optional dataset ID to specifically target a dataset
    """
    return StreamingResponse(
        stream_graph_updates(user_input, dataset_id=dataset_id),
        media_type="text/event-stream",
    )
