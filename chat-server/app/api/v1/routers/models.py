from fastapi import APIRouter, HTTPException

from app.models.router import ModelInfo
from app.utils.model_registry.model_config import AVAILABLE_MODELS

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
