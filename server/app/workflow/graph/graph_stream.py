import json
import logging
from typing import AsyncGenerator, List, Optional

from app.workflow.graph import graph


async def stream_graph_updates(
    user_input: str,
    dataset_ids: Optional[List[str]] = None,
    project_ids: Optional[List[str]] = None,
) -> AsyncGenerator[str, None]:
    """Stream graph updates for user input with event tracking.

    Args:
        user_input (str): The user's input query
        dataset_ids (List[str], optional): Specific dataset IDs to use for the query

    Yields:
        str: JSON-formatted event data for streaming
    """
    input_state = {
        "messages": [{"role": "user", "content": user_input}],
        "dataset_ids": dataset_ids,
        "project_ids": project_ids,
    }

    try:
        async for event in graph.astream_events(input_state, version="v2"):
            if event.get("event", None) == "on_custom_event":
                formatted_event = event.get("data", {})
                logging.info(formatted_event)
                yield json.dumps(formatted_event) + "\n\n"
    except Exception as e:
        error_event = json.dumps(
            {
                "type": "error",
                "message": f"Error during streaming: {str(e)}",
                "data": {"error": str(e)},
            },
            indent=2,
        )
        yield error_event + "\n\n"