from typing import Type

from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from app.core.config import settings

from .base import BaseLLMProvider


class LiteLLMProvider(BaseLLMProvider):
    def __init__(
        self,
        metadata: dict[str, str],
    ):
        self.metadata = metadata

        self.litellm_key_header_name = settings.LITELLM_KEY_HEADER_NAME
        self.litellm_virtual_key = settings.LITELLM_VIRTUAL_KEY
        self.litellm_master_key = settings.LITELLM_MASTER_KEY

        # Must have one of master_key or (virtual_key and key_header_name)
        if not self.litellm_master_key and not (
            self.litellm_virtual_key and self.litellm_key_header_name
        ):
            raise ValueError(
                "Must have one of master_key or (virtual_key"
                "and key_header_name) for litellm provider"
            )
        if self.litellm_master_key:
            self.headers = {
                "Authorization": f"Bearer {self.litellm_master_key}",
            }
        else:
            self.headers = {
                self.litellm_key_header_name: self.litellm_virtual_key,
            }

    def get_llm_model(
        self,
        model_name: str,
        streaming: bool = True,
        temperature: float | None = None,
        json_mode: bool = False,
        schema: Type[BaseModel] | None = None,
    ):
        kwargs = {
            "api_key": "X",
            "base_url": settings.LITELLM_BASE_URL,
            "model": model_name,
            "default_headers": self.headers,
            "extra_body": {
                "metadata": {
                    **self.metadata,
                },
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
