from typing import Type

from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from app.core.config import settings

from .base import BaseLLMProvider


class OpenRouterLLMProvider(BaseLLMProvider):
    def __init__(self, metadata: dict[str, str]):
        self.metadata = metadata

    def get_llm_model(
        self,
        model_name: str,
        streaming: bool = True,
        temperature: float | None = None,
        json_mode: bool = False,
        schema: Type[BaseModel] | None = None,
    ):
        kwargs = {
            "api_key": settings.OPENROUTER_API_KEY,
            "base_url": settings.OPENROUTER_BASE_URL,
            "model": model_name,
            "metadata": {
                **self.metadata,
            },
            "streaming": streaming,
        }

        if temperature is not None:
            kwargs["temperature"] = temperature

        llm = ChatOpenAI(**kwargs)

        if json_mode:
            if schema:
                return llm.with_structured_output(schema)
            else:
                return llm.with_structured_output(method="json_mode")
        else:
            return llm
