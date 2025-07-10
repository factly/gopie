import json

from langchain_openai import ChatOpenAI

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

    def get_llm_model(self, model_name: str, streaming: bool = True) -> ChatOpenAI:
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

        return ChatOpenAI(
            api_key="X",  # type: ignore
            base_url=base_url,
            default_headers=headers,
            model=model_name,
            streaming=streaming,
        )
