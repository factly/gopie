from langchain_openai import ChatOpenAI

from app.core.config import settings

from .base import BaseLLMProvider


class CustomLLMProvider(BaseLLMProvider):
    def __init__(self, metadata: dict[str, str]):
        self.metadata = metadata

    def get_llm_model(
        self,
        model_name: str,
        streaming: bool = True,
        temperature: float | None = None,
        json_mode: bool = False,
    ):
        kwargs = {
            "api_key": settings.CUSTOM_LLM_API_KEY,
            "base_url": settings.CUSTOM_LLM_BASE_URL,
            "model": model_name,
            "metadata": {
                **self.metadata,
            },
            "streaming": streaming,
        }

        if temperature is not None:
            kwargs["temperature"] = temperature

        llm = ChatOpenAI(**kwargs)

        return llm.with_structured_output(method="json_mode") if json_mode else llm
