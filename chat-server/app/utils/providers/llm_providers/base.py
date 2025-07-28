from abc import ABC, abstractmethod

from langchain_core.language_models import BaseChatModel


class BaseLLMProvider(ABC):
    @abstractmethod
    def get_llm_model(
        self,
        model_name: str,
        streaming: bool = True,
        temperature: float | None = None,
        json_mode: bool = False,
    ) -> BaseChatModel:
        """
        Get an LLM model instance.

        Args:
            model_name: Name of the model to use
            streaming: Whether to enable streaming
            temperature: Temperature setting for the model
            json_mode: Whether to enable JSON mode using with_structured_output

        Returns:
            BaseChatModel instance, potentially with structured output enabled
        """
        pass
