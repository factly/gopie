from abc import ABC, abstractmethod

from langchain_openai import ChatOpenAI


class BaseProvider(ABC):
    @abstractmethod
    def get_openai_model(
        self, model_name: str, streaming: bool = True
    ) -> ChatOpenAI:
        pass

    @abstractmethod
    def get_gemini_model(
        self, model_name: str, streaming: bool = True
    ) -> ChatOpenAI:
        pass
