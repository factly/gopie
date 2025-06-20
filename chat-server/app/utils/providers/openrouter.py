from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from app.core.config import settings


class OpenrouterGatewayProvider:
    def __init__(self, user: str, trace_id: str):
        self.user = user
        self.trace_id = trace_id

    def get_openai_model(self, model_name: str):
        return ChatOpenAI(
            api_key=settings.OPENROUTER_API_KEY,  # type: ignore
            base_url=settings.OPENROUTER_BASE_URL,
            model=f"openai/{model_name}",
            metadata={
                "user": self.user,
                "trace_id": self.trace_id,
                "project": "gopie-chat-server",
            },
        )

    def get_gemini_model(self, model_name: str):
        return ChatOpenAI(
            api_key=settings.OPENROUTER_API_KEY,  # type: ignore
            base_url=settings.OPENROUTER_BASE_URL,
            model=f"google/{model_name}",
            metadata={
                "user": self.user,
                "trace_id": self.trace_id,
                "project": "gopie-chat-server",
            },
        )

    def get_embeddings_model(self, model_name: str):
        return OpenAIEmbeddings(
            api_key=settings.OPENROUTER_API_KEY,  # type: ignore
            base_url=settings.OPENROUTER_BASE_URL,
            model=f"openai/{model_name}",
        )
