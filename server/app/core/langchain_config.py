from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from portkey_ai import PORTKEY_GATEWAY_URL, createHeaders
from app.core.config import settings

from app.tools import TOOLS

class ModelConfig:
    def __init__(self):
        self.model = settings.OPENAI_MODEL
        self.embeddings_model = settings.OPENAI_EMBEDDINGS_MODEL

        portkey_api_key = settings.PORTKEY_API_KEY
        virtual_key = settings.VIRTUAL_KEY

        self.portkey_headers = createHeaders(
            api_key=portkey_api_key, virtual_key=virtual_key
        )

class LangchainConfig:
    def __init__(self, config: ModelConfig):
        self.config = config

        model = ChatOpenAI(
            api_key="X",  # type: ignore
            base_url=PORTKEY_GATEWAY_URL,
            default_headers=config.portkey_headers,
            model=config.model,
        )

        self.embeddings_model = OpenAIEmbeddings(
            api_key="X",  # type: ignore
            base_url=PORTKEY_GATEWAY_URL,
            default_headers=config.portkey_headers,
            model=config.embeddings_model,
        )
        self.llm = model.bind_tools(list(TOOLS.values()))


lc = LangchainConfig(ModelConfig())
