from typing import Generic, Type, TypeVar, cast

from langchain_core.messages import BaseMessage
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel

from app.core.config import settings
from app.models.provider import EmbeddingProvider, LLMProvider
from app.tool_utils.tools import ToolNames, get_tools
from app.utils.model_registry.model_selection import (
    get_node_model,
    get_node_temperature,
    requires_json_mode,
)
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

T = TypeVar("T", bound=BaseModel)


class StructuredLLM(Generic[T]):
    """
    Type hint interface for LLMs that return structured Pydantic models.
    This provides clean type inference for the specific Pydantic model type.
    """

    async def ainvoke(self, input) -> T:
        """Async invoke that returns the specified Pydantic model type."""
        ...

    def invoke(self, input) -> T:
        """Sync invoke that returns the specified Pydantic model type."""
        ...


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
        json_mode: bool = False,
        temperature: float | None = None,
        schema: Type[BaseModel] | None = None,
    ):
        self.metadata = metadata
        self.llm_provider = get_llm_provider(metadata)
        self.embedding_provider = get_embedding_provider(metadata)
        self.json_mode = json_mode
        self.temperature = temperature
        self.schema = schema

    def _create_llm(self, model_id: str):
        model = self.llm_provider.get_llm_model(
            model_id, temperature=self.temperature, json_mode=self.json_mode, schema=self.schema
        )
        return model

    def _create_llm_with_tools(
        self,
        model_id: str,
        tool_names: list[ToolNames],
    ):
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

    def get_llm_for_node(
        self,
        node_name: str,
        tool_names: list[ToolNames] | None = None,
    ):
        model_id = get_node_model(node_name)
        return (
            self.get_llm_with_tools(node_name, tool_names) if tool_names else self.get_llm(model_id)
        )


def get_model_provider(
    config: RunnableConfig = RunnableConfig(),
    json_mode: bool = False,
    temperature: float | None = None,
    schema: Type[BaseModel] | None = None,
) -> ModelProvider:
    metadata = config.get("configurable", {}).get("metadata", {})
    return ModelProvider(
        metadata=metadata, json_mode=json_mode, temperature=temperature, schema=schema
    )


def get_chat_history(config: RunnableConfig) -> list[BaseMessage]:
    return config.get("configurable", {}).get("chat_history", [])


def get_configured_llm_for_node(
    node_name: str,
    config: RunnableConfig,
    *,
    tool_names: list[ToolNames] | None = None,
    schema: Type[T] | None = None,
) -> StructuredLLM[T]:
    """
    Get a configured LLM for a workflow node with type inference.

    Args:
        node_name: Name of the workflow node
        config: Runnable configuration
        tool_names: Optional list of tools to bind to the LLM
        schema: Pydantic model class for structured output (required for type inference)

    Returns:
        Configured LLM that returns the specified Pydantic model type

    Example:
        llm = get_configured_llm_for_node("validate_input", config, schema=ValidateInputOutput)
        result = await llm.ainvoke(prompt)  # result is typed as ValidateInputOutput
    """
    json_mode = requires_json_mode(node_name)
    temperature = get_node_temperature(node_name)

    model_provider = get_model_provider(
        config, json_mode=json_mode, temperature=temperature, schema=schema
    )
    llm = model_provider.get_llm_for_node(node_name, tool_names)

    return cast(StructuredLLM[T], llm)
