import json
from typing import Type

from langchain_openai import ChatOpenAI
from pydantic import BaseModel

from app.core.config import settings

from .base import BaseLLMProvider


class CloudflareLLMProvider(BaseLLMProvider):
    def __init__(
        self,
        metadata: dict[str, str],
    ):
        self.metadata = metadata
        base_url = settings.CLOUDFLARE_GATEWAY_URL
        provider = settings.CLOUDFLARE_PROVIDER
        account_id = settings.CLOUDFLARE_ACCOUNT_ID
        gateway_id = settings.CLOUDFLARE_GATEWAY_ID

        self.openai_compat_url = f"{base_url}/{provider}/{account_id}/{gateway_id}/compat"

    def get_llm_model(
        self,
        model_name: str,
        streaming: bool = True,
        temperature: float | None = None,
        json_mode: bool = False,
        schema: Type[BaseModel] | None = None,
    ):
        base_url = self.openai_compat_url

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.CLOUDFLARE_PROVIDER_API_KEY}",
            "cf-aig-authorization": f"Bearer {settings.CLOUDFLARE_API_TOKEN}",
            "cf-aig-metadata": json.dumps(
                {
                    **self.metadata,
                }
            ),
        }

        kwargs = {
            "api_key": "X",
            "base_url": base_url,
            "default_headers": headers,
            "model": model_name,
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
