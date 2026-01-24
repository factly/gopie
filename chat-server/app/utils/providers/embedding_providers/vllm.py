from typing import Any

from langchain_openai import OpenAIEmbeddings

from app.core.config import settings

from .base import BaseEmbeddingProvider

TASK_DESCRIPTION = "Given a web search query, retrieve relevant passages that answer the query"


class VLLMEmbeddingFunctionProvider(OpenAIEmbeddings):
    def embed_query(self, text: str, **kwargs: Any) -> list[float]:
        text = f"Instruct: {TASK_DESCRIPTION}\nQuery: {text}"
        return super().embed_query(
            text, model_kwargs={"extra_body": {"truncate_prompt_tokens": -1}}, **kwargs
        )

    async def aembed_query(self, text: str, **kwargs: Any) -> list[float]:
        text = f"Instruct: {TASK_DESCRIPTION}\nQuery: {text}"
        return await super().aembed_query(
            text, model_kwargs={"extra_body": {"truncate_prompt_tokens": -1}}, **kwargs
        )


class VLLMEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(
        self,
        metadata: dict[str, str],
    ):
        pass

    def get_embeddings_model(self, model_name: str) -> OpenAIEmbeddings:
        return VLLMEmbeddingFunctionProvider(
            base_url=settings.CUSTOM_EMBEDDING_BASE_URL,
            api_key=settings.CUSTOM_EMBEDDING_API_KEY,  # type: ignore
            model=model_name,
        )
