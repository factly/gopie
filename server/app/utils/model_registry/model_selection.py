from typing import Optional

from app.models.router import ModelInfo
from server.app.utils.model_registry.model_config import AVAILABLE_MODELS

NODE_TO_MODEL = {
    "analyze_query": "gpt-4o",
    "plan_query": "gpt-4o",
    "generate_subqueries": "gpt-4o",
    "execute_query": "gpt-4o-mini",
    "identify_datasets": "gpt-4o-mini",
    "analyze_dataset": "gpt-4o-mini",
    "extract_summary": "gpt-4o-mini",
    "validate_query_result": "gpt-4o-mini",
}


def get_model_info(model_id: str) -> Optional[ModelInfo]:
    """Get information about a specific model"""
    return AVAILABLE_MODELS.get(model_id)
