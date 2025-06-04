import uuid

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from portkey_ai import PORTKEY_GATEWAY_URL, createHeaders

from app.core.config import settings
from app.models.provider import ModelVendor
from app.tools import TOOLS
from app.utils.langsmith.prompt_manager import get_prompt
from app.utils.model_registry.model_config import AVAILABLE_MODELS


class ModelConfig:
    def __init__(
        self,
        user: str | None = "gopie.chat.server",
        trace_id: str | None = None,
        model_id: str | None = None,
    ):
        self.user = user
        self.trace_id = trace_id or str(uuid.uuid4())
        self.model_provider = ModelVendor.OPENAI

        self.openai_model = settings.DEFAULT_OPENAI_MODEL
        self.openai_embeddings_model = settings.DEFAULT_EMBEDDING_MODEL
        self.gemini_model = settings.DEFAULT_GEMINI_MODEL

        if model_id and model_id in AVAILABLE_MODELS:
            self._set_model_from_id(model_id)

        self.openai_headers = self._create_openai_headers()
        self.gemini_headers = self._create_gemini_headers()

    def _set_model_from_id(self, model_id: str) -> None:
        model_info = AVAILABLE_MODELS[model_id]
        provider = model_info.provider

        if provider == ModelVendor.OPENAI:
            self.openai_model = model_id
            self.model_provider = ModelVendor.OPENAI
        elif provider == ModelVendor.GOOGLE:
            self.gemini_model = model_id
            self.model_provider = ModelVendor.GOOGLE

    def _create_openai_headers(self):
        return createHeaders(
            api_key=settings.PORTKEY_API_KEY,
            virtual_key=settings.OPENAI_VIRTUAL_KEY,
            trace_id=self.trace_id,
            metadata={
                "_user": self.user,
                "project": "gopie-chat-server",
            },
        )

    def _create_gemini_headers(self):
        return createHeaders(
            api_key=settings.PORTKEY_API_KEY,
            virtual_key=settings.GEMINI_VIRTUAL_KEY,
            trace_id=self.trace_id,
            metadata={
                "_user": self.user,
                "project": "gopie-chat-server",
            },
        )


class LangchainConfig:
    def __init__(self, config: ModelConfig):
        self.config = config
        self.llm = self._create_llm()
        self.prompt_chain = self._create_prompt_chain()
        self.llm_with_tools = self._create_llm_with_tools()
        self.llm_prompt_chain = self._create_llm_prompt_chain()
        self.embeddings_model = self._create_embeddings_model()

    def _create_llm(self):
        if self.config.model_provider == ModelVendor.GOOGLE:
            model = self._create_gemini_model()
        else:
            model = self._create_openai_model()

        return model

    def _create_prompt_chain(self):
        system_prompt = get_prompt("system_prompt")

        return ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}"),
            ]
        )

    def _create_llm_with_tools(self):
        return self.llm.bind_tools(list(TOOLS.values()))

    def _create_llm_prompt_chain(self):
        return self.prompt_chain | self.llm_with_tools

    def _create_openai_model(self):
        return ChatOpenAI(
            api_key="X",  # type: ignore
            base_url=PORTKEY_GATEWAY_URL,
            default_headers=self.config.openai_headers,
            model=self.config.openai_model,
            streaming=True,
        )

    def _create_gemini_model(self):
        return ChatOpenAI(
            api_key="X",  # type: ignore
            base_url=PORTKEY_GATEWAY_URL,
            default_headers=self.config.gemini_headers,
            model=self.config.gemini_model,
            streaming=True,
        )

    def _create_embeddings_model(self):
        return OpenAIEmbeddings(
            api_key="X",  # type: ignore
            base_url=PORTKEY_GATEWAY_URL,
            default_headers=self.config.openai_headers,
            model=self.config.openai_embeddings_model,
        )
