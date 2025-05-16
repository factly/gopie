from langchain_core.runnables import RunnableConfig

from app.core.langchain_config import LangchainConfig, ModelConfig


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

    def get_embeddings_model(self):
        model_config = ModelConfig(
            model_id=self.model_id, trace_id=self.trace_id
        )
        return LangchainConfig(model_config).embeddings_model

    def get_custom_model(self, model_id: str):
        model_config = ModelConfig(model_id=model_id, trace_id=self.trace_id)
        return LangchainConfig(model_config).llm


def model_provider(
    config: RunnableConfig,
):
    model_id = config.get("configurable", {}).get("model_id")
    trace_id = config.get("configurable", {}).get("trace_id")
    return ModelProvider(model_id=model_id, trace_id=trace_id)
