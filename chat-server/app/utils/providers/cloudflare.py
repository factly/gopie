from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from app.core.config import settings
from app.utils.providers.base import BaseProvider


class CloudflareGatewayProvider(BaseProvider):
    def __init__(
        self,
        user: str,
        trace_id: str,
    ):
        self.user = user
        self.trace_id = trace_id

        url = f"{settings.CLOUDFLARE_GATEWAY_URL}"
        url = url.replace(
            "{account_id}/{gateway_id}",
            f"{settings.CLOUDFLARE_ACCOUNT_ID}/"
            f"{settings.CLOUDFLARE_GATEWAY_ID}",
        )

        self.base_url = url

    def get_openai_model(
        self, model_name: str, streaming: bool = True
    ) -> ChatOpenAI:
        base_url = f"{self.base_url}/openai"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
            "cf-aig-authorization": f"Bearer {settings.CLOUDFLARE_API_TOKEN}",
        }

        return ChatOpenAI(
            api_key="X",  # type: ignore
            base_url=base_url,
            default_headers=headers,
            model=model_name,
            streaming=streaming,
        )

    def get_gemini_model(
        self, model_name: str, streaming: bool = True
    ) -> ChatOpenAI:
        base_url = f"{self.base_url}/compat"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.GOOGLE_API_KEY}",
            "cf-aig-authorization": f"Bearer {settings.CLOUDFLARE_API_TOKEN}",
        }

        formatted_model = f"google-ai-studio/{model_name}"

        return ChatOpenAI(
            api_key="X",  # type: ignore
            base_url=base_url,
            default_headers=headers,
            model=formatted_model,
            streaming=streaming,
        )

    def get_embeddings_model(self, model_name: str) -> OpenAIEmbeddings:
        return OpenAIEmbeddings(
            api_key="X",  # type: ignore
            base_url=self.base_url,
            model=model_name,
        )
