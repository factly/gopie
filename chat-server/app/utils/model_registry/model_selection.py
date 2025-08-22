from dataclasses import dataclass

from langchain_core.messages import BaseMessage
from langchain_core.runnables import RunnableConfig

from app.core.config import settings
from app.models.provider import ModelCategory, TemperatureCategory


@dataclass
class NodeConfig:
    """Configuration for a workflow node's LLM settings"""

    complexity: ModelCategory
    temperature: TemperatureCategory
    json_mode: bool = False

    @property
    def model_id(self) -> str:
        """Get the model ID based on complexity"""
        match self.complexity:
            case ModelCategory.FAST:
                return settings.FAST_MODEL or settings.DEFAULT_LLM_MODEL
            case ModelCategory.BALANCED:
                return settings.BALANCED_MODEL or settings.DEFAULT_LLM_MODEL
            case ModelCategory.ADVANCED:
                return settings.ADVANCED_MODEL or settings.DEFAULT_LLM_MODEL
            case _:
                return settings.DEFAULT_LLM_MODEL


NODE_CONFIGS = {
    "analyze_query": NodeConfig(ModelCategory.FAST, TemperatureCategory.NONE),
    "route_query_replan": NodeConfig(ModelCategory.FAST, TemperatureCategory.DETERMINISTIC),
    "validate_input": NodeConfig(
        ModelCategory.FAST, TemperatureCategory.DETERMINISTIC, json_mode=True
    ),
    "validate_result": NodeConfig(
        ModelCategory.BALANCED, TemperatureCategory.DETERMINISTIC, json_mode=True
    ),
    "check_visualization": NodeConfig(ModelCategory.FAST, TemperatureCategory.DETERMINISTIC),
    "identify_datasets": NodeConfig(
        ModelCategory.BALANCED, TemperatureCategory.DETERMINISTIC, json_mode=True
    ),
    "plan_query": NodeConfig(
        ModelCategory.ADVANCED, TemperatureCategory.LOW_VARIATION, json_mode=True
    ),
    "plan_sql_query_tool": NodeConfig(
        ModelCategory.ADVANCED, TemperatureCategory.LOW_VARIATION, json_mode=True
    ),
    "visualize_data": NodeConfig(ModelCategory.FAST, TemperatureCategory.LOW_VARIATION),
    "process_query": NodeConfig(
        ModelCategory.ADVANCED, TemperatureCategory.BALANCED, json_mode=True
    ),
    "process_context": NodeConfig(
        ModelCategory.BALANCED, TemperatureCategory.BALANCED, json_mode=True
    ),
    "generate_subqueries": NodeConfig(
        ModelCategory.ADVANCED, TemperatureCategory.BALANCED, json_mode=True
    ),
    "stream_updates": NodeConfig(
        ModelCategory.BALANCED, TemperatureCategory.CREATIVE, json_mode=True
    ),
    "generate_result": NodeConfig(ModelCategory.BALANCED, TemperatureCategory.CREATIVE),
    "response": NodeConfig(ModelCategory.BALANCED, TemperatureCategory.CREATIVE),
}

EXTERNAL_FUNCTION_CONFIGS = {
    "generate_col_descriptions": NodeConfig(
        ModelCategory.BALANCED, TemperatureCategory.BALANCED, json_mode=True
    ),
    "progress_message": NodeConfig(ModelCategory.FAST, TemperatureCategory.CREATIVE),
}


def get_node_config(node_name: str) -> NodeConfig:
    if node_name in NODE_CONFIGS:
        return NODE_CONFIGS[node_name]

    if node_name in EXTERNAL_FUNCTION_CONFIGS:
        return EXTERNAL_FUNCTION_CONFIGS[node_name]

    return NodeConfig(ModelCategory.BALANCED, TemperatureCategory.BALANCED, json_mode=False)


def get_node_temperature(node_name: str) -> float | None:
    return get_node_config(node_name).temperature.value


def requires_json_mode(node_name: str) -> bool:
    return get_node_config(node_name).json_mode


def get_node_model(node_name: str) -> str:
    return get_node_config(node_name).model_id


def get_chat_history(config: RunnableConfig) -> list[BaseMessage]:
    return config.get("configurable", {}).get("chat_history", [])
