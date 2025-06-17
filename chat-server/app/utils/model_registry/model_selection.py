from app.core.config import settings
from app.models.router import ModelInfo
from app.utils.model_registry.model_config import AVAILABLE_MODELS

NODE_TO_MODEL = {
    "analyze_query": settings.MODEL_ANALYZE_QUERY,
    "route_query_replan": settings.MODEL_ROUTE_QUERY_REPLAN,
    "generate_subqueries": settings.MODEL_GENERATE_SUBQUERIES,
    "identify_datasets": settings.MODEL_IDENTIFY_DATASETS,
    "plan_query": settings.MODEL_PLAN_QUERY,
    "generate_result": settings.MODEL_GENERATE_RESULT,
    "stream_updates": settings.MODEL_STREAM_UPDATES,
    "check_further_execution_requirement": (
        settings.MODEL_CHECK_FURTHER_EXECUTION_REQUIREMENT
    ),
    # Single dataset graph nodes
    "process_query": settings.MODEL_PROCESS_QUERY,
    "response": settings.MODEL_RESPONSE,
    "supervisor": settings.DEFAULT_OPENAI_MODEL,
    # Visualization graph nodes
    "choose_visualization": settings.DEFAULT_OPENAI_MODEL,
    "format_data_for_visualization": settings.DEFAULT_OPENAI_MODEL,
    "visualization_response": settings.MODEL_GENERATE_RESULT,
}


def get_model_info(model_id: str) -> ModelInfo:
    model_info = AVAILABLE_MODELS.get(model_id)

    if model_info is None:
        default_model_info = AVAILABLE_MODELS.get(
            settings.DEFAULT_OPENAI_MODEL
        )
        if default_model_info is None:
            raise ValueError(
                f"Default model {settings.DEFAULT_OPENAI_MODEL} not found"
            )
        return default_model_info

    return model_info
