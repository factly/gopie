from typing import List, Optional

from app.workflow.graph import stream_graph_updates
from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="server/app/tests/templates")


@router.get("/")
async def root():
    """Entry point for the application."""
    return {"message": "Welcome to the Database Agent API"}


@router.get("/test")
async def test(request: Request):
    return templates.TemplateResponse("stream_test.html", {"request": request})


@router.get("/query")
async def get_nl2sql(
    user_input: str = Query(
        ..., description="The natural language query from the user"
    ),
    dataset_ids: Optional[List[str]] = Query(..., description="List of dataset IDs"),
):
    """Stream the agent's processing events as Server-Sent Events.

    Args:
        user_input: The natural language query from the user
        dataset_ids (List[str], optional): Specific dataset IDs to use for the query
    """
    print(dataset_ids)

    return StreamingResponse(
        stream_graph_updates(user_input, dataset_ids=dataset_ids),
        media_type="text/event-stream",
    )
