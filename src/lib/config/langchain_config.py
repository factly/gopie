import openai
from portkey_ai import PORTKEY_GATEWAY_URL
from langchain_openai import ChatOpenAI
from src.tools import TOOLS
from .config import Config, config

class LangchainConfig:
    def __init__(self, config: Config):
        self.config = config

        model = ChatOpenAI(
            api_key="X", # type: ignore
            base_url=PORTKEY_GATEWAY_URL,
            default_headers=config.portkey_headers,
            model=config.model,
        )

        self.llm = model.bind_tools(list(TOOLS.values()))

lc = LangchainConfig(config)
