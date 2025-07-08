from langchain_openai import OpenAIEmbeddings

from app.core.config import settings
from app.utils.embedding_providers.base import BaseEmbeddingProvider


class LiteLLMEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(
        self,
        metadata: dict[str, str],
    ):
        self.metadata = metadata
        self.headers = {
            "Authorization": f"Bearer {settings.LITELLM_MASTER_KEY}",
        }

    def get_embeddings_model(self, model_name: str) -> OpenAIEmbeddings:
        return OpenAIEmbeddings(
            api_key="X",  # type: ignore
            base_url=settings.LITELLM_BASE_URL,
            default_headers=self.headers,
            model=model_name,
        )
