from langchain_openai import OpenAIEmbeddings

from app.core.config import settings


def get_embeddings_model(metadata: dict | None = None) -> OpenAIEmbeddings:
    model_name = settings.DEFAULT_EMBEDDING_MODEL

    return OpenAIEmbeddings(
        api_key=settings.OPENAI_API_KEY,  # type: ignore
        model=model_name,
    )
