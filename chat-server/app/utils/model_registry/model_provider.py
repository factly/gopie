from typing import Dict, List, Optional

from langchain_core.runnables import RunnableConfig

from app.core.config import settings
from app.models.provider import EmbeddingProvider, LLMProvider, ModelVendor
from app.tool_utils.tools import ToolNames, get_tools
from app.utils.embedding_providers import (
    BaseEmbeddingProvider,
    CustomEmbeddingProvider,
    LiteLLMEmbeddingProvider,
    OpenAIEmbeddingProvider,
    PortkeyEmbeddingProvider,
    PortkeySelfHostedEmbeddingProvider,
)
from app.utils.llm_providers import (
    BaseLLMProvider,
    CloudflareLLMProvider,
    CustomLLMProvider,
    LiteLLMProvider,
    OpenRouterLLMProvider,
    PortkeyLLMProvider,
    PortkeySelfHostedLLMProvider,
)
from app.utils.model_registry.model_config import AVAILABLE_MODELS
from app.utils.model_registry.model_selection import get_node_model


def get_llm_provider(metadata: Dict[str, str]) -> BaseLLMProvider:
    gateway_type = LLMProvider(settings.GATEWAY_PROVIDER)
    match gateway_type:
        case LLMProvider.PORTKEY_HOSTED:
            return PortkeyLLMProvider(metadata)
        case LLMProvider.PORTKEY_SELF_HOSTED:
            return PortkeySelfHostedLLMProvider(metadata)
        case LLMProvider.LITELLM:
            return LiteLLMProvider(metadata)
        case LLMProvider.CLOUDFLARE:
            return CloudflareLLMProvider(metadata)
        case LLMProvider.OPENROUTER:
            return OpenRouterLLMProvider(metadata)
        case LLMProvider.CUSTOM:
            return CustomLLMProvider(metadata)


def get_embedding_provider(metadata: Dict[str, str]) -> BaseEmbeddingProvider:
    gateway_type = EmbeddingProvider(settings.GATEWAY_PROVIDER)
    match gateway_type:
        case EmbeddingProvider.PORTKEY_HOSTED:
            return PortkeyEmbeddingProvider(metadata)
        case EmbeddingProvider.PORTKEY_SELF_HOSTED:
            return PortkeySelfHostedEmbeddingProvider(metadata)
        case EmbeddingProvider.LITELLM:
            return LiteLLMEmbeddingProvider(metadata)
        case EmbeddingProvider.OPENAI:
            return OpenAIEmbeddingProvider(metadata)
        case EmbeddingProvider.CUSTOM:
            return CustomEmbeddingProvider(metadata)


class ModelConfig:
    def __init__(
        self,
        model_id: str | None = None,
    ):
        self.model_provider = ModelVendor(settings.DEFAULT_VENDOR)

        self.openai_model = settings.DEFAULT_OPENAI_MODEL
        self.gemini_model = settings.DEFAULT_GEMINI_MODEL

        if model_id and model_id in AVAILABLE_MODELS:
            self._set_model_from_id(model_id)

    def _set_model_from_id(self, model_id: str) -> None:
        model_info = AVAILABLE_MODELS[model_id]
        provider = model_info.provider

        if provider == ModelVendor.OPENAI:
            self.openai_model = model_id
            self.model_provider = ModelVendor.OPENAI
        elif provider == ModelVendor.GOOGLE:
            self.gemini_model = model_id
            self.model_provider = ModelVendor.GOOGLE


class ModelProvider:
    def __init__(
        self,
        metadata: Dict[str, str],
    ):
        self.metadata = metadata
        self.llm_provider = get_llm_provider(metadata)
        self.embedding_provider = get_embedding_provider(metadata)

    def _create_llm(self, model_id: str):
        model_config = ModelConfig(model_id=model_id)
        if model_config.model_provider == ModelVendor.GOOGLE:
            model = self.llm_provider.get_gemini_model(
                model_config.gemini_model
            )
        else:
            model = self.llm_provider.get_openai_model(
                model_config.openai_model
            )

        return model

    def _create_llm_with_tools(
        self, model_id: str, tool_names: List[ToolNames]
    ):
        tools = get_tools(tool_names)
        tool_functions = [tool for tool, _ in tools.values()]
        llm = self._create_llm(model_id)
        return llm.bind_tools(tool_functions)

    def _create_embeddings_model(self):
        return self.embedding_provider.get_embeddings_model(
            settings.DEFAULT_EMBEDDING_MODEL
        )

    def get_llm(self, model_id: str):
        return self._create_llm(model_id)

    def get_llm_with_tools(self, model_id: str, tool_names: List[ToolNames]):
        return self._create_llm_with_tools(model_id, tool_names)

    def get_embeddings_model(self):
        return self._create_embeddings_model()

    def get_llm_for_node(
        self, node_name: str, tool_names: Optional[List[ToolNames]] = None
    ):
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


def get_chat_history(config: RunnableConfig):
    return config.get("configurable", {}).get("chat_history", [])
