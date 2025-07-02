from abc import ABC, abstractmethod

from langchain_openai import OpenAIEmbeddings


class BaseEmbeddingProvider(ABC):
    @abstractmethod
    def get_embeddings_model(self, model_name: str) -> OpenAIEmbeddings:
        pass
