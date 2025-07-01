from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.utils.providers.base import BaseProvider


class OpenrouterGatewayProvider(BaseProvider):
    def __init__(self, metadata: dict[str, str]):
        self.metadata = metadata

    def get_openai_model(self, model_name: str):
        return ChatOpenAI(
            api_key=settings.OPENROUTER_API_KEY,  # type: ignore
            base_url=settings.OPENROUTER_BASE_URL,
            model=f"openai/{model_name}",
            metadata={
                **self.metadata,
            },
        )

    def get_gemini_model(self, model_name: str):
        return ChatOpenAI(
            api_key=settings.OPENROUTER_API_KEY,  # type: ignore
            base_url=settings.OPENROUTER_BASE_URL,
            model=f"google/{model_name}",
            metadata={
                **self.metadata,
            },
        )
