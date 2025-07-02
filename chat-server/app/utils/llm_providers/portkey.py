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

    def get_headers(self, virtual_key: str):
        return createHeaders(
            api_key=settings.PORTKEY_API_KEY,
            virtual_key=virtual_key,
            trace_id=self.trace_id,
            chat_id=self.chat_id,
            metadata={
                "_user": self.user,
                **self.metadata,
            },
        )

    def get_openai_model(
        self, model_name: str, streaming: bool = True
    ) -> ChatOpenAI:
        headers = self.get_headers(settings.OPENAI_VIRTUAL_KEY)

        return ChatOpenAI(
            api_key="X",  # type: ignore
            base_url=PORTKEY_GATEWAY_URL,
            default_headers=headers,
            model=model_name,
            streaming=streaming,
        )

    def get_gemini_model(
        self, model_name: str, streaming: bool = True
    ) -> ChatOpenAI:
        headers = self.get_headers(settings.GEMINI_VIRTUAL_KEY)

        return ChatOpenAI(
            api_key="X",  # type: ignore
            base_url=PORTKEY_GATEWAY_URL,
            default_headers=headers,
            model=model_name,
            streaming=streaming,
        )
