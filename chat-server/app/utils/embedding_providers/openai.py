from langchain_openai import OpenAIEmbeddings

from app.core.config import settings
from app.utils.embedding_providers.base import BaseEmbeddingProvider


class OpenAIEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(
        self,
        metadata: dict[str, str],
    ):
        pass

    def get_embeddings_model(self, model_name: str) -> OpenAIEmbeddings:
        return OpenAIEmbeddings(
            api_key=settings.OPENAI_API_KEY,  # type: ignore
            model=model_name,
        )
