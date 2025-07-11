from abc import ABC, abstractmethod

from langchain_openai import ChatOpenAI


class BaseLLMProvider(ABC):
    @abstractmethod
    def get_llm_model(self, model_name: str, streaming: bool = True) -> ChatOpenAI:
        pass
