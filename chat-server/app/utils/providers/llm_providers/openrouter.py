from langchain_openai import ChatOpenAI

from app.core.config import settings

from .base import BaseLLMProvider


class OpenRouterLLMProvider(BaseLLMProvider):
    def __init__(self, metadata: dict[str, str]):
        self.metadata = metadata

    def get_llm_model(self, model_name: str, streaming: bool = True):
        return ChatOpenAI(
            api_key=settings.OPENROUTER_API_KEY,  # type: ignore
            base_url=settings.OPENROUTER_BASE_URL,
            model=model_name,
            metadata={
                **self.metadata,
            },
            streaming=streaming,
        )
