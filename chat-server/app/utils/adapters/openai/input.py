from openai.types.chat.completion_create_params import (
    CompletionCreateParamsNonStreaming as RequestNonStreaming,
)
from openai.types.chat.completion_create_params import (
    CompletionCreateParamsStreaming as RequestStreaming,
)

from app.models.router import Message, QueryRequest


def from_openai_format(
    request: RequestNonStreaming | RequestStreaming,
) -> QueryRequest:
    """
    Convert OpenAI API request format to internal QueryRequest format.
    Handles both streaming and non-streaming requests.

    Args:
        request: Either a streaming or non-streaming OpenAI request

    Returns:
        QueryRequest: Internal request format
    """
    # Convert messages from OpenAI format to internal format
    messages = [
        Message(
            role=message.get("role"),
            content=str(message.get("content", "")),
        )
        for message in request.get("messages")
    ]

    project_ids: list[str] = []
    dataset_ids: list[str] = []

    metadata = request.get("metadata")

    if metadata:
        for key, value in metadata.items():
            if key.startswith("project_id"):
                project_ids.extend(value.split(","))
            elif key.startswith("dataset_id"):
                dataset_ids.extend(value.split(","))
    project_ids = [project_id.strip() for project_id in project_ids if project_id.strip()]
    dataset_ids = [dataset_id.strip() for dataset_id in dataset_ids if dataset_id.strip()]
    return QueryRequest(
        messages=messages,
        model_id=request.get("model"),
        user=request.get("user"),
        dataset_ids=dataset_ids,
        project_ids=project_ids,
    )
