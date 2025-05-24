from app.models.router import ModelInfo
from app.utils.model_registry.model_config import (
    AVAILABLE_MODELS,
    DEFAULT_MODEL,
)

NODE_TO_MODEL = {
    "analyze_query": "gemini-2.0-flash",
    "route_query_replan": "gemini-2.0-flash",
    "generate_subqueries": "gemini-2.5-flash-preview-04-17",
    "identify_datasets": "gemini-2.5-flash-preview-04-17",
    "plan_query": "gemini-2.5-flash-preview-04-17",
    "generate_result": "gemini-2.5-flash-preview-04-17",
    "stream_updates": "gemini-2.5-flash-preview-04-17",
    "check_further_execution_requirement": "gemini-2.0-flash",
}

# NODE_TO_MODEL = {
#     "analyze_query": "o3-mini",
#     "route_query_replan": "o3-mini",
#     "generate_subqueries": "o3-mini",
#     "identify_datasets": "o3-mini",
#     "plan_query": "o3-mini",
#     "generate_result": "o3-mini",
#     "stream_updates": "o3-mini",
#     "check_further_execution_requirement": "o3-mini",
# }


def get_model_info(model_id: str) -> ModelInfo:
    model_info = AVAILABLE_MODELS.get(model_id)

    if model_info is None:
        default_model_info = AVAILABLE_MODELS.get(DEFAULT_MODEL)
        if default_model_info is None:
            raise ValueError(f"Default model {DEFAULT_MODEL} not found")
        return default_model_info

    return model_info
