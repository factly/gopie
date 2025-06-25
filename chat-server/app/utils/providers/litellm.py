from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from app.core.config import settings
from app.utils.providers.base import BaseProvider


class LiteLLMGatewayProvider(BaseProvider):
    def __init__(
        self,
        user: str,
        trace_id: str,
    ):
        self.user = user
        self.trace_id = trace_id
        self.headers = {
            "Authorization": f"Bearer {settings.LITELLM_MASTER_KEY}",
        }

    def get_openai_model(
        self, model_name: str, streaming: bool = True
    ) -> ChatOpenAI:
        return ChatOpenAI(
            api_key="X",  # type: ignore
            base_url=settings.LITELLM_BASE_URL,
            model=model_name,
            default_headers=self.headers,
            streaming=streaming,
            extra_body={
                "metadata": {
                    "user": self.user,
                    "trace_id": self.trace_id,
                },
            },
        )

    def get_gemini_model(
        self, model_name: str, streaming: bool = True
    ) -> ChatOpenAI:
        return ChatOpenAI(
            api_key="X",  # type: ignore
            base_url=settings.LITELLM_BASE_URL,
            model=model_name,
            default_headers=self.headers,
            streaming=streaming,
            extra_body={
                "metadata": {
                    "user": self.user,
                    "trace_id": self.trace_id,
                },
            },
        )

    def get_embeddings_model(self, model_name: str) -> OpenAIEmbeddings:
        return OpenAIEmbeddings(
            api_key="X",  # type: ignore
            base_url=settings.LITELLM_BASE_URL,
            default_headers=self.headers,
            model=model_name,
        )
