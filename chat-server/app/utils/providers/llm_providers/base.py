from abc import ABC, abstractmethod

from langchain_openai import ChatOpenAI


class BaseLLMProvider(ABC):
    @abstractmethod
    def get_llm_model(
        self,
        model_name: str,
    ) -> ChatOpenAI:
        """
        Get an LLM model instance.

        Args:
            model_name: Name of the model to use

        Returns:
            ChatOpenAI instance
        """
        pass
