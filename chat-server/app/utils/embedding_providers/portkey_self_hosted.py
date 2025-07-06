import json

from langchain_openai import OpenAIEmbeddings

from app.core.config import settings
from app.utils.embedding_providers.base import BaseEmbeddingProvider


class PortkeySelfHostedEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(
        self,
        metadata: dict[str, str],
    ):
        self.user = metadata.pop("user", "")
        self.trace_id = metadata.pop("trace_id", "")
        self.chat_id = metadata.pop("chat_id", "")
        self.metadata = metadata
        self.headers = {
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
            "x-portkey-trace-id": self.trace_id,
            "x-portkey-metadata": json.dumps(
                {
                    "_user": self.user,
                    "chat_id": self.chat_id,
                    **self.metadata,
                }
            ),
        }

    def get_embeddings_model(self, model_name: str) -> OpenAIEmbeddings:
        return OpenAIEmbeddings(
            api_key="X",  # type: ignore
            base_url=settings.PORTKEY_SELF_HOSTED_URL,
            default_headers=self.headers,
            model=model_name,
        )
