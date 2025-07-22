from langchain_core.messages import BaseMessage
from langchain_core.runnables import RunnableConfig

from app.core.config import settings
from app.models.provider import EmbeddingProvider, LLMProvider
from app.tool_utils.tools import ToolNames, get_tools
from app.utils.model_registry.model_selection import get_node_model
from app.utils.providers.embedding_providers import (
    BaseEmbeddingProvider,
    CustomEmbeddingProvider,
    LiteLLMEmbeddingProvider,
    OpenAIEmbeddingProvider,
    PortkeyEmbeddingProvider,
)
from app.utils.providers.llm_providers import (
    BaseLLMProvider,
    CloudflareLLMProvider,
    CustomLLMProvider,
    LiteLLMProvider,
    OpenRouterLLMProvider,
    PortkeyLLMProvider,
)


def get_llm_provider(metadata: dict[str, str]) -> BaseLLMProvider:
    gateway_type = LLMProvider(settings.LLM_GATEWAY_PROVIDER)
    match gateway_type:
        case LLMProvider.PORTKEY:
            return PortkeyLLMProvider(metadata)
        case LLMProvider.LITELLM:
            return LiteLLMProvider(metadata)
        case LLMProvider.CLOUDFLARE:
            return CloudflareLLMProvider(metadata)
        case LLMProvider.OPENROUTER:
            return OpenRouterLLMProvider(metadata)
        case LLMProvider.CUSTOM:
            return CustomLLMProvider(metadata)


def get_embedding_provider(metadata: dict[str, str]) -> BaseEmbeddingProvider:
    gateway_type = EmbeddingProvider(settings.EMBEDDING_GATEWAY_PROVIDER)
    match gateway_type:
        case EmbeddingProvider.PORTKEY:
            return PortkeyEmbeddingProvider(metadata)
        case EmbeddingProvider.LITELLM:
            return LiteLLMEmbeddingProvider(metadata)
        case EmbeddingProvider.OPENAI:
            return OpenAIEmbeddingProvider(metadata)
        case EmbeddingProvider.CUSTOM:
            return CustomEmbeddingProvider(metadata)


class ModelProvider:
    def __init__(
        self,
        metadata: dict[str, str],
    ):
        self.metadata = metadata
        self.llm_provider = get_llm_provider(metadata)
        self.embedding_provider = get_embedding_provider(metadata)

    def _create_llm(self, model_id: str):
        model = self.llm_provider.get_llm_model(model_id)
        return model

    def _create_llm_with_tools(self, model_id: str, tool_names: list[ToolNames]):
        tools = get_tools(tool_names)
        tool_functions = [tool for tool, _ in tools.values()]
        llm = self._create_llm(model_id)
        return llm.bind_tools(tool_functions)

    def _create_embeddings_model(self):
        return self.embedding_provider.get_embeddings_model(settings.DEFAULT_EMBEDDING_MODEL)

    def get_llm(self, model_id: str):
        return self._create_llm(model_id)

    def get_embeddings_model(self):
        return self._create_embeddings_model()

    def get_llm_with_tools(self, node_name: str, tool_names: list[ToolNames]):
        model_id = get_node_model(node_name)
        return self._create_llm_with_tools(model_id, tool_names)

    def get_llm_for_node(self, node_name: str, tool_names: list[ToolNames] | None = None):
        model_id = get_node_model(node_name)
        if tool_names:
            return self.get_llm_with_tools(model_id, tool_names)
        return self.get_llm(model_id)


def get_model_provider(
    config: RunnableConfig = RunnableConfig(),
):
    metadata = config.get("configurable", {}).get("metadata", {})
    return ModelProvider(metadata=metadata)


def get_custom_model(model_id: str):
    return ModelProvider(metadata={}).get_llm(model_id=model_id)


def get_chat_history(config: RunnableConfig) -> list[BaseMessage]:
    return config.get("configurable", {}).get("chat_history", [])
