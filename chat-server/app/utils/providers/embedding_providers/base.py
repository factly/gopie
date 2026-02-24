from abc import ABC, abstractmethod

from langchain_openai import OpenAIEmbeddings


class BaseEmbeddingProvider(ABC):
    """
    Abstract base class for embedding providers.

    All providers return OpenAIEmbeddings because it provides a standard
    interface that's compatible with OpenAI-style API endpoints used by
    most embedding services (OpenAI, LiteLLM, Portkey, etc.).
    """

    @abstractmethod
    def get_embeddings_model(self, model_name: str) -> OpenAIEmbeddings:
        """
        Get an embeddings model instance for the specified model.

        Args:
            model_name: Name of the embedding model to use
                       (e.g., "text-embedding-ada-002", "text-embedding-3-small")

        Returns:
            OpenAIEmbeddings: Configured embeddings model instance

        Raises:
            ValueError: If the model_name is invalid or not supported
            ConnectionError: If unable to connect to the embedding service
        """
        pass
