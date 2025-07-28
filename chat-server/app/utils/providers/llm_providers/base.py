from abc import ABC, abstractmethod
from typing import Type

from langchain_core.language_models import BaseChatModel
from pydantic import BaseModel


class BaseLLMProvider(ABC):
    @abstractmethod
    def get_llm_model(
        self,
        model_name: str,
        streaming: bool = True,
        temperature: float | None = None,
        json_mode: bool = False,
        schema: Type[BaseModel] | None = None,
    ) -> BaseChatModel:
        """
        Get an LLM model instance.

        Args:
            model_name: Name of the model to use
            streaming: Whether to enable streaming
            temperature: Temperature setting for the model
            json_mode: Whether to enable JSON mode using with_structured_output
            schema: Pydantic model class for structured output (when json_mode=True)

        Returns:
            BaseChatModel instance, potentially with structured output enabled
        """
        pass
