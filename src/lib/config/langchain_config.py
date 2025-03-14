from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_openai import ChatOpenAI
from portkey_ai import PORTKEY_GATEWAY_URL
from pydantic import SecretStr

from src.tools import TOOLS

from .config import Config, config


class LangchainConfig:
    def __init__(self, config: Config):
        self.config = config

        model = ChatOpenAI(
            api_key="X",  # type: ignore
            base_url=PORTKEY_GATEWAY_URL,
            default_headers=config.portkey_headers,
            model=config.model,
        )

        self.embedding_model = GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004",
            google_api_key=SecretStr(config.gemini_api_key or ""),
        )
        self.llm = model.bind_tools(list(TOOLS.values()))


lc = LangchainConfig(config)
