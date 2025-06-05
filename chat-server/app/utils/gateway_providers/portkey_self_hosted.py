import json

from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from app.core.config import settings


class PortkeySelfHostedGatewayProvider:
    def __init__(
        self,
        user: str,
        trace_id: str,
    ):
        self.user = user
        self.trace_id = trace_id

        self.headers = {
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
            "x-portkey-provider": "openai",
            "x-portkey-trace-id": self.trace_id,
            "x-portkey-metadata": json.dumps(
                {
                    "_user": self.user,
                    "project": "gopie-chat-server",
                }
            ),
        }

    def get_openai_model(
        self, model_name: str, streaming: bool = True
    ) -> ChatOpenAI:
        return ChatOpenAI(
            api_key="X",  # type: ignore
            base_url=settings.PORTKEY_SELF_HOSTED_URL,
            default_headers=self.headers,
            model=model_name,
            streaming=streaming,
        )

    def get_gemini_model(
        self, model_name: str, streaming: bool = True
    ) -> ChatOpenAI:
        gemini_headers = self.headers.copy()
        gemini_headers["x-portkey-provider"] = "google"
        gemini_headers["Authorization"] = f"Bearer {settings.GOOGLE_API_KEY}"

        return ChatOpenAI(
            api_key="X",  # type: ignore
            base_url=settings.PORTKEY_SELF_HOSTED_URL,
            default_headers=gemini_headers,
            model=model_name,
            streaming=streaming,
        )

    def get_embeddings_model(self, model_name: str) -> OpenAIEmbeddings:
        return OpenAIEmbeddings(
            api_key="X",  # type: ignore
            base_url=settings.PORTKEY_SELF_HOSTED_URL,
            default_headers=self.headers,
            model=model_name,
        )
