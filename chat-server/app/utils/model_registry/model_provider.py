from typing import List, Optional

from langchain_core.runnables import RunnableConfig

from app.core.config import settings
from app.models.provider import GatewayProvider, ModelVendor
from app.tool_utils.tools import ToolNames, get_tools
from app.utils.model_registry.model_config import AVAILABLE_MODELS
from app.utils.model_registry.model_selection import get_node_model
from app.utils.providers.base import BaseProvider
from app.utils.providers.cloudflare import CloudflareGatewayProvider
from app.utils.providers.litellm import LiteLLMGatewayProvider
from app.utils.providers.openrouter import OpenrouterGatewayProvider
from app.utils.providers.portkey import PortkeyGatewayProvider
from app.utils.providers.portkey_self_hosted import (
    PortkeySelfHostedGatewayProvider,
)


def get_gateway_provider(user: str, trace_id: str) -> BaseProvider:
    gateway_type = GatewayProvider(settings.GATEWAY_PROVIDER)
    if gateway_type == GatewayProvider.PORTKEY_HOSTED:
        return PortkeyGatewayProvider(user=user, trace_id=trace_id)
    elif gateway_type == GatewayProvider.PORTKEY_SELF_HOSTED:
        return PortkeySelfHostedGatewayProvider(user=user, trace_id=trace_id)
    elif gateway_type == GatewayProvider.LITELLM:
        return LiteLLMGatewayProvider(user=user, trace_id=trace_id)
    elif gateway_type == GatewayProvider.CLOUDFLARE:
        return CloudflareGatewayProvider(user=user, trace_id=trace_id)
    elif gateway_type == GatewayProvider.OPENROUTER:
        return OpenrouterGatewayProvider(user=user, trace_id=trace_id)
    else:
        raise ValueError(f"Unsupported gateway provider: {gateway_type}")


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
        trace_id: str = "",
        user: str = "",
    ):
        self.trace_id = trace_id
        self.user = user
        self.gateway_provider = get_gateway_provider(user, trace_id)

    def _create_llm(self, model_id: str):
        model_config = ModelConfig(model_id=model_id)
        if model_config.model_provider == ModelVendor.GOOGLE:
            model = self.gateway_provider.get_gemini_model(
                model_config.gemini_model
            )
        else:
            model = self.gateway_provider.get_openai_model(
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
        return self.gateway_provider.get_embeddings_model(
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
    config: RunnableConfig,
):
    trace_id = config.get("configurable", {}).get("trace_id", "")
    user = config.get("configurable", {}).get("user", "")
    return ModelProvider(trace_id=trace_id, user=user)


def get_custom_model(model_id: str):
    return ModelProvider().get_llm(model_id=model_id)


def get_chat_history(config: RunnableConfig):
    return config.get("configurable", {}).get("chat_history", [])
