from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from portkey_ai import PORTKEY_GATEWAY_URL, createHeaders

from app.core.config import settings
from app.tools import TOOLS


class ModelConfig:
    def __init__(self):
        portkey_api_key = settings.PORTKEY_API_KEY

        self.model = settings.OPENAI_MODEL
        self.embeddings_model = settings.OPENAI_EMBEDDINGS_MODEL
        openai_virtual_key = settings.OPENAI_VIRTUAL_KEY

        self.gemini_model = settings.GEMINI_MODEL
        gemini_virtual_key = settings.GEMINI_VIRTUAL_KEY

        self.gemini_headers = createHeaders(
            api_key=portkey_api_key, virtual_key=gemini_virtual_key
        )

        self.openai_headers = createHeaders(
            api_key=portkey_api_key, virtual_key=openai_virtual_key
        )


class LangchainConfig:
    def __init__(self, config: ModelConfig):
        self.config = config

        model = ChatOpenAI(
            api_key="X",  # type: ignore
            base_url=PORTKEY_GATEWAY_URL,
            default_headers=config.gemini_headers,
            model=config.gemini_model,
        )

        self.embeddings_model = OpenAIEmbeddings(
            api_key="X",  # type: ignore
            base_url=PORTKEY_GATEWAY_URL,
            default_headers=config.openai_headers,
            model=config.embeddings_model,
        )

        self.llm = model.bind_tools(list(TOOLS.values()))


lc = LangchainConfig(ModelConfig())
