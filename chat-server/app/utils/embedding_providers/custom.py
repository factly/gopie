from langchain_openai import OpenAIEmbeddings

from app.core.config import settings
from app.utils.embedding_providers.base import BaseEmbeddingProvider


class CustomEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(
        self,
        metadata: dict[str, str],
    ):
        pass

    def get_embeddings_model(self, model_name: str) -> OpenAIEmbeddings:
        return OpenAIEmbeddings(
            base_url=settings.CUSTOM_EMBEDDING_BASE_URL,
            api_key=settings.CUSTOM_EMBEDDING_API_KEY,  # type: ignore
            model=model_name,
        )
