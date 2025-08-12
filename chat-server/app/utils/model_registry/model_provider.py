from typing import Generic, Optional, Type, TypeVar, Union

from langchain_core.messages import BaseMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from pydantic import BaseModel
from typing_extensions import overload

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

StructuredOutputType = TypeVar("StructuredOutputType", bound=BaseModel)


class StructuredLLM(Generic[StructuredOutputType]):
    """
    Type hint interface for LLMs that return structured Pydantic models.
    This provides clean type inference for the specific Pydantic model type.
    """

    async def ainvoke(self, input) -> StructuredOutputType:
        """Async invoke that returns the specified Pydantic model type."""
        ...

    def invoke(self, input) -> StructuredOutputType:
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
    ):
        self.metadata = metadata
        self.llm_provider = get_llm_provider(metadata)
        self.embedding_provider = get_embedding_provider(metadata)

    def get_llm(self, model_id: str):
        model = self.llm_provider.get_llm_model(model_id)
        return model

    def get_llm_with_tools(
        self,
        model_id: str,
        tool_names: list[ToolNames],
    ):
        tools = get_tools(tool_names)
        tool_functions = [tool for tool, _ in tools.values()]
        llm = self.get_llm(model_id)
        return llm.bind_tools(tool_functions)

    def get_embeddings_model(self):
        return self.embedding_provider.get_embeddings_model(settings.DEFAULT_EMBEDDING_MODEL)


def get_model_provider(
    config: RunnableConfig = RunnableConfig(),
) -> ModelProvider:
    metadata = config.get("configurable", {}).get("metadata", {})
    return ModelProvider(metadata=metadata)


def get_chat_history(config: RunnableConfig) -> list[BaseMessage]:
    return config.get("configurable", {}).get("chat_history", [])


@overload
def get_configured_llm_for_node(
    node_name: str,
    config: RunnableConfig,
    *,
    tool_names: list[ToolNames] | None = None,
    schema: None = None,
) -> ChatOpenAI:
    ...


@overload
def get_configured_llm_for_node(
    node_name: str,
    config: RunnableConfig,
    *,
    tool_names: list[ToolNames] | None = None,
    schema: Type[StructuredOutputType],
) -> StructuredLLM[StructuredOutputType]:
    ...


def get_configured_llm_for_node(
    node_name: str,
    config: RunnableConfig,
    *,
    tool_names: list[ToolNames] | None = None,
    force_tool_calls: bool = False,
    schema: Optional[Type[StructuredOutputType]] = None,
) -> Union[ChatOpenAI, StructuredLLM[StructuredOutputType]]:
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
    model_id = get_node_model(node_name)

    model_provider = get_model_provider(config)
    if tool_names:
        llm = model_provider.get_llm_with_tools(model_id, tool_names)
    else:
        llm = model_provider.get_llm(model_id)
    if temperature:
        llm = llm.bind(temperature=temperature)
    if schema:
        structured_llm = llm.with_structured_output(schema=schema, method="json_schema")
        return structured_llm
    elif json_mode:
        llm = llm.bind(response_format={"type": "json_object"})
    if force_tool_calls:
        llm = llm.bind(tool_choice=True)
    return llm


def get_llm_for_other_task(node_name: str, config: RunnableConfig):
    json_mode = requires_json_mode(node_name)
    temperature = get_node_temperature(node_name)
    model_id = get_node_model(node_name)

    model_provider = get_model_provider(config)
    llm = model_provider.get_llm(model_id)
    if temperature:
        llm = llm.bind(temperature=temperature)
    if json_mode:
        llm = llm.bind(response_format={"type": "json_object"})
    return model_provider.get_llm(model_id)
