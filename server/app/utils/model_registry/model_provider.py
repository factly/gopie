from langchain_core.runnables import RunnableConfig

from app.core.langchain_config import LangchainConfig, ModelConfig
from app.utils.model_registry.model_config import DEFAULT_MODEL
from app.utils.model_registry.model_selection import NODE_TO_MODEL


class ModelProvider:
    def __init__(
        self,
        model_id: str | None = None,
        trace_id: str | None = None,
    ):
        self.model_id = model_id
        self.trace_id = trace_id

    def get_llm(self):
        model_config = ModelConfig(
            model_id=self.model_id, trace_id=self.trace_id
        )
        return LangchainConfig(model_config).llm

    def get_llm_prompt_chain(self):
        model_config = ModelConfig(
            model_id=self.model_id, trace_id=self.trace_id
        )
        return LangchainConfig(model_config).llm_prompt_chain

    def get_llm_with_tools(self):
        model_config = ModelConfig(
            model_id=self.model_id, trace_id=self.trace_id
        )
        return LangchainConfig(model_config).llm_with_tools

    def get_embeddings_model(self):
        model_config = ModelConfig(
            model_id=self.model_id, trace_id=self.trace_id
        )
        return LangchainConfig(model_config).embeddings_model


def get_model_provider(
    config: RunnableConfig,
):
    model_id = config.get("configurable", {}).get("model_id")
    trace_id = config.get("configurable", {}).get("trace_id")
    return ModelProvider(model_id=model_id, trace_id=trace_id)


def get_llm_for_node(
    node_name: str, config: RunnableConfig, with_tools: bool = False
):
    model_id = NODE_TO_MODEL.get(node_name, DEFAULT_MODEL)
    trace_id = config.get("configurable", {}).get("trace_id")

    if with_tools:
        return ModelProvider(
            model_id=model_id, trace_id=trace_id
        ).get_llm_with_tools()
    else:
        return ModelProvider(model_id=model_id, trace_id=trace_id).get_llm()


def get_custom_model(model_id: str):
    return ModelProvider(model_id=model_id).get_llm()
