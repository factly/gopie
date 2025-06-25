from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from portkey_ai import PORTKEY_GATEWAY_URL, createHeaders

from app.core.config import settings
from app.utils.providers.base import BaseProvider


class PortkeyGatewayProvider(BaseProvider):
    def __init__(
        self,
        user: str,
        trace_id: str,
    ):
        self.user = user
        self.trace_id = trace_id

    def get_headers(self, virtual_key: str):
        return createHeaders(
            api_key=settings.PORTKEY_API_KEY,
            virtual_key=virtual_key,
            trace_id=self.trace_id,
            metadata={
                "_user": self.user,
                "project": "gopie-chat-server",
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

    def get_embeddings_model(self, model_name: str) -> OpenAIEmbeddings:
        headers = self.get_headers(settings.OPENAI_VIRTUAL_KEY)

        return OpenAIEmbeddings(
            api_key="X",  # type: ignore
            base_url=PORTKEY_GATEWAY_URL,
            default_headers=headers,
            model=model_name,
        )
