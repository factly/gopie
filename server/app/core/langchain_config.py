import uuid

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from portkey_ai import PORTKEY_GATEWAY_URL, createHeaders

from app.core.config import settings
from app.core.system_prompt import SYSTEM_PROMPT
from app.tools import TOOLS


class ModelConfig:
    def __init__(self, trace_id=None):
        portkey_api_key = settings.PORTKEY_API_KEY

        self.model = settings.OPENAI_MODEL
        self.embeddings_model = settings.OPENAI_EMBEDDINGS_MODEL
        openai_virtual_key = settings.OPENAI_VIRTUAL_KEY

        self.gemini_model = settings.GEMINI_MODEL
        gemini_virtual_key = settings.GEMINI_VIRTUAL_KEY

        self.trace_id = trace_id or str(uuid.uuid4())

        self.gemini_headers = createHeaders(
            api_key=portkey_api_key,
            virtual_key=gemini_virtual_key,
            trace_id=self.trace_id,
        )

        self.openai_headers = createHeaders(
            api_key=portkey_api_key,
            virtual_key=openai_virtual_key,
            trace_id=self.trace_id,
        )


class LangchainConfig:
    def __init__(self, config: ModelConfig):
        self.config = config

        model = ChatOpenAI(
            api_key="X",  # type: ignore
            base_url=PORTKEY_GATEWAY_URL,
            default_headers=config.gemini_headers,
            model=config.gemini_model,
            streaming=True,
        )

        self.embeddings_model = OpenAIEmbeddings(
            api_key="X",  # type: ignore
            base_url=PORTKEY_GATEWAY_URL,
            default_headers=config.openai_headers,
            model=config.embeddings_model,
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", SYSTEM_PROMPT),
                ("human", "{input}"),
            ]
        )

        self.llm = prompt | model.bind_tools(list(TOOLS.values()))


lc = LangchainConfig(ModelConfig())


def get_llm_with_trace(trace_id=None):
    return LangchainConfig(ModelConfig(trace_id=trace_id)).llm


def get_embeddings_model_with_trace(trace_id=None):
    return LangchainConfig(ModelConfig(trace_id=trace_id)).embeddings_model
