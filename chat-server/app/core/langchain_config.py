from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from app.core.config import settings
from app.models.provider import GatewayProvider, ModelVendor
from app.tools import TOOLS
from app.utils.gateway_providers.cloudflare import CloudflareGatewayProvider
from app.utils.gateway_providers.litellm import LiteLLMGatewayProvider
from app.utils.gateway_providers.openrouter import OpenrouterGatewayProvider
from app.utils.gateway_providers.portkey import PortkeyGatewayProvider
from app.utils.gateway_providers.portkey_self_hosted import (
    PortkeySelfHostedGatewayProvider,
)
from app.utils.langsmith.prompt_manager import get_prompt
from app.utils.model_registry.model_config import AVAILABLE_MODELS


class ModelConfig:
    def __init__(
        self,
        trace_id: str,
        user: str,
        model_id: str | None = None,
    ):
        self.user = user
        self.trace_id = trace_id
        self.model_provider = ModelVendor.OPENAI

        self.openai_model = settings.DEFAULT_OPENAI_MODEL
        self.openai_embeddings_model = settings.DEFAULT_EMBEDDING_MODEL
        self.gemini_model = settings.DEFAULT_GEMINI_MODEL

        if model_id and model_id in AVAILABLE_MODELS:
            self._set_model_from_id(model_id)

        self.gateway_provider = self._create_gateway_provider()

    def _set_model_from_id(self, model_id: str) -> None:
        model_info = AVAILABLE_MODELS[model_id]
        provider = model_info.provider

        if provider == ModelVendor.OPENAI:
            self.openai_model = model_id
            self.model_provider = ModelVendor.OPENAI
        elif provider == ModelVendor.GOOGLE:
            self.gemini_model = model_id
            self.model_provider = ModelVendor.GOOGLE

    def _create_gateway_provider(self):
        gateway_type = GatewayProvider(settings.GATEWAY_PROVIDER)

        if gateway_type == GatewayProvider.PORTKEY_HOSTED:
            return PortkeyGatewayProvider(
                user=self.user, trace_id=self.trace_id
            )
        elif gateway_type == GatewayProvider.PORTKEY_SELF_HOSTED:
            return PortkeySelfHostedGatewayProvider(
                user=self.user, trace_id=self.trace_id
            )
        elif gateway_type == GatewayProvider.LITELLM:
            return LiteLLMGatewayProvider(
                user=self.user, trace_id=self.trace_id
            )
        elif gateway_type == GatewayProvider.CLOUDFLARE:
            return CloudflareGatewayProvider(
                user=self.user, trace_id=self.trace_id
            )
        elif gateway_type == GatewayProvider.OPENROUTER:
            return OpenrouterGatewayProvider(
                user=self.user, trace_id=self.trace_id
            )
        else:
            raise ValueError(f"Unsupported gateway provider: {gateway_type}")


class LangchainConfig:
    def __init__(self, config: ModelConfig):
        self.config = config
        self.llm = self._create_llm()
        self.prompt_chain = self._create_prompt_chain()
        self.llm_with_tools = self._create_llm_with_tools()
        self.llm_prompt_chain = self._create_llm_prompt_chain()
        self.embeddings_model = self._create_embeddings_model()

    def _create_llm(self):
        if self.config.model_provider == ModelVendor.GOOGLE:
            model = self.config.gateway_provider.get_gemini_model(
                self.config.gemini_model
            )
        else:
            model = self.config.gateway_provider.get_openai_model(
                self.config.openai_model
            )

        return model

    def _create_prompt_chain(self):
        system_prompt = get_prompt("system_prompt")

        return ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}"),
            ]
        )

    def _create_llm_with_tools(self):
        return self.llm.bind_tools(list(TOOLS.values()))

    def _create_llm_prompt_chain(self):
        return self.prompt_chain | self.llm_with_tools

    def _create_embeddings_model(self):
        return self.config.gateway_provider.get_embeddings_model(
            self.config.openai_embeddings_model
        )

    def get_gateway_info(self) -> dict:
        return {
            "gateway_provider": settings.GATEWAY_PROVIDER,
            "model_provider": self.config.model_provider.value,
            "openai_model": self.config.openai_model,
            "gemini_model": self.config.gemini_model,
            "embeddings_model": self.config.openai_embeddings_model,
            "trace_id": self.config.trace_id,
            "user": self.config.user,
        }
