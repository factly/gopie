from app.core.config import settings
from app.models.provider import ModelCategory

NODE_TO_COMPLEXITY = {
    "analyze_query": ModelCategory.ADVANCED,
    "route_query_replan": ModelCategory.FAST,
    "generate_subqueries": ModelCategory.ADVANCED,
    "identify_datasets": ModelCategory.BALANCED,
    "plan_query": ModelCategory.ADVANCED,
    "generate_result": ModelCategory.BALANCED,
    "stream_updates": ModelCategory.BALANCED,
    "check_further_execution_requirement": ModelCategory.FAST,
    "process_query": ModelCategory.ADVANCED,
    "check_visualization": ModelCategory.FAST,
    "response": ModelCategory.BALANCED,
    "choose_visualization": ModelCategory.BALANCED,
    "format_data_for_visualization": ModelCategory.FAST,
    "visualization_response": ModelCategory.BALANCED,
}


COMPLEXITY_TO_MODEL = {
    ModelCategory.FAST: settings.FAST_MODEL,
    ModelCategory.BALANCED: settings.BALANCED_MODEL,
    ModelCategory.ADVANCED: settings.ADVANCED_MODEL,
}


def get_node_complexity(node_name: str) -> ModelCategory:
    return NODE_TO_COMPLEXITY.get(node_name, ModelCategory.BALANCED)


def get_node_model(node_name: str) -> str:
    complexity = get_node_complexity(node_name)
    model_id = COMPLEXITY_TO_MODEL[complexity]

    if not model_id:
        model_id = settings.DEFAULT_OPENAI_MODEL
        if not model_id:
            raise ValueError(
                f"No model configured for {complexity.value} complexity "
                f"and no default model available"
            )

    return model_id
