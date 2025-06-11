from langchain_core.runnables import RunnableConfig

from app.core.langchain_config import LangchainConfig, ModelConfig
from app.utils.model_registry.model_selection import NODE_TO_MODEL


class ModelProvider:
    def __init__(
        self,
        trace_id: str,
        user: str,
        model_id: str | None = None,
        with_tools: bool = False,
    ):
        self.model_id = model_id
        self.trace_id = trace_id
        self.with_tools = with_tools
        self.user = user

    def get_llm(self):
        model_config = ModelConfig(
            model_id=self.model_id, trace_id=self.trace_id, user=self.user
        )

        lc_config = LangchainConfig(model_config)
        return lc_config.llm

    def get_node_llm(self):
        model_config = ModelConfig(
            model_id=self.model_id,
            trace_id=self.trace_id,
            user=self.user,
        )

        lc_config = LangchainConfig(model_config)

        if self.with_tools:
            return lc_config.prompt_chain | lc_config.llm_with_tools
        else:
            return lc_config.prompt_chain | lc_config.llm

    def get_embeddings_model(self):
        model_config = ModelConfig(
            model_id=self.model_id, trace_id=self.trace_id, user=self.user
        )
        return LangchainConfig(model_config).embeddings_model


def get_model_provider(
    config: RunnableConfig,
):
    model_id = config.get("configurable", {}).get("model_id")
    trace_id = config.get("configurable", {}).get("trace_id", "")
    user = config.get("configurable", {}).get("user", "")
    return ModelProvider(model_id=model_id, trace_id=trace_id, user=user)


def get_llm_for_node(
    node_name: str, config: RunnableConfig, with_tools: bool = False
):
    model_id = NODE_TO_MODEL.get(node_name)
    trace_id = config.get("configurable", {}).get("trace_id", "")
    user = config.get("configurable", {}).get("user", "")

    return ModelProvider(
        model_id=model_id, trace_id=trace_id, with_tools=with_tools, user=user
    ).get_node_llm()


def get_custom_model(model_id: str):
    return ModelProvider(model_id=model_id, trace_id="", user="").get_llm()


def get_chat_history(config: RunnableConfig):
    return config.get("configurable", {}).get("chat_history", [])
