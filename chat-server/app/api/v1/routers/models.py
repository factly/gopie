from fastapi import APIRouter, HTTPException

from app.models.router import ModelInfo
from app.utils.model_registry.model_config import AVAILABLE_MODELS
from app.utils.model_registry.model_selection import (
    get_node_complexity,
    get_node_model,
)

router = APIRouter()


@router.get("/")
async def list_models() -> list[ModelInfo]:
    """
    Returns a list of available reasoning models.

    These models can be used for the reasoning tasks in the application.
    """
    return list(AVAILABLE_MODELS.values())


@router.get("/{model_id}")
async def get_model(model_id: str) -> ModelInfo:
    """
    Returns information about a specific model by ID.
    """
    if model_id not in AVAILABLE_MODELS:
        raise HTTPException(
            status_code=404, detail=f"Model with ID '{model_id}' not found"
        )

    return AVAILABLE_MODELS[model_id]


@router.get("/nodes/info")
async def get_nodes_info() -> list:
    """
    Returns comprehensive information about all workflow nodes including
    their streaming configuration, role, and model assignments.
    """
    nodes_info = []

    for node_name in AVAILABLE_MODELS.keys():
        complexity = get_node_complexity(node_name)
        assigned_model = get_node_model(node_name)

        node_info = {
            "node_name": node_name,
            "complexity": complexity.value,
            "assigned_model": assigned_model,
        }
        nodes_info.append(node_info)

    return sorted(nodes_info, key=lambda x: x["node_name"])
