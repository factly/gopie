from typing import Dict

from langchain_openai import ChatOpenAI
from portkey_ai import PORTKEY_GATEWAY_URL, createHeaders

from app.core.config import settings
from app.utils.llm_providers.base import BaseLLMProvider


class PortkeyLLMProvider(BaseLLMProvider):
    def __init__(
        self,
        metadata: Dict[str, str],
    ):
        self.user = metadata.pop("user", "")
        self.trace_id = metadata.pop("trace_id", "")
        self.chat_id = metadata.pop("chat_id", "")
        self.metadata = metadata
        self.provider_api_key = settings.PORTKEY_PROVIDER_API_KEY
        self.provider_name = settings.PORTKEY_PROVIDER_NAME
        self.config = settings.PORTKEY_CONFIG_ID
        self.base_url = settings.PORTKEY_URL
        if not self.base_url:
            self.base_url = PORTKEY_GATEWAY_URL
            self.self_hosted = False
        else:
            self.self_hosted = True
        # Must have provider_api_key or config if self_hosted is true
        if self.self_hosted and not (self.provider_api_key or self.config):
            raise ValueError(
                "Must have provider_api_key or config for self-hosted portkey"
            )

    def get_headers(self):
        headers = {
            "api_key": settings.PORTKEY_API_KEY,
            "trace_id": self.trace_id,
            "chat_id": self.chat_id,
            "metadata": {
                "_user": self.user,
                **self.metadata,
            },
        }
        if self.config:
            headers["config"] = self.config
        if self.provider_name:
            headers["provider"] = self.provider_name
        return createHeaders(
            **headers,
        )

    def get_llm_model(
        self, model_name: str, streaming: bool = True
    ) -> ChatOpenAI:
        headers = self.get_headers()
        if self.self_hosted:
            provider_api_key = self.provider_api_key
        else:
            provider_api_key = "X"
        return ChatOpenAI(
            api_key=provider_api_key,
            base_url=self.base_url,
            default_headers=headers,
            model=model_name,
            streaming=streaming,
        )
