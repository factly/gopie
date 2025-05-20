from app.models.router import ModelInfo
from app.utils.model_registry.model_config import (
    AVAILABLE_MODELS,
    DEFAULT_MODEL,
)

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


def get_model_info(model_id: str) -> ModelInfo:
    model_info = AVAILABLE_MODELS.get(model_id)

    if model_info is None:
        default_model_info = AVAILABLE_MODELS.get(DEFAULT_MODEL)
        if default_model_info is None:
            raise ValueError(f"Default model {DEFAULT_MODEL} not found")
        return default_model_info

    return model_info
