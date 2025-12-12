from .base import BaseEmbeddingProvider


class LocalEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(
        self,
        metadata: dict[str, str],
    ):
        pass

    def get_embeddings_model(self, model_name: str):
        from langchain_community.embeddings import Model2vecEmbeddings

        return Model2vecEmbeddings(model_name)
