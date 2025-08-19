from langchain_core.messages import BaseMessage
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnableConfig, RunnableLambda

from app.core.config import settings
from app.core.log import logger
from app.utils.langsmith.client import pull_prompt
from app.utils.model_registry.model_provider import get_configured_llm_for_node
from app.workflow.prompts.prompt_selector import NodeName, PromptSelector


class PromptManager:
    """
    Manages prompt retrieval from LangSmith with fallback support.
    """

    def __init__(self, prompt_name: NodeName, **kwargs):
        self.prompt_selector = PromptSelector()
        self.prompt_name: NodeName = prompt_name
        self.kwargs = kwargs

    def _get_formatted_input(self) -> dict | None:
        return self.prompt_selector.format_prompt_input(node_name=self.prompt_name, **self.kwargs)

    def _is_langsmith_enabled(self) -> bool:
        return settings.LANGSMITH_PROMPT

    def get_prompt_template(self) -> ChatPromptTemplate:
        """
        Get a prompt template from LangSmith hub if enabled, otherwise return fallback.
        """

        if self._is_langsmith_enabled():
            try:
                langsmith_prompt = pull_prompt(self.prompt_name)
                return langsmith_prompt

            except Exception as e:
                logger.warning(
                    f"Failed to load LangSmith prompt "
                    f"'{self.prompt_name}': {e}. "
                    f"Using fallback prompt instead."
                )

                return self.prompt_selector.get_prompt_template(self.prompt_name)

        else:
            return self.prompt_selector.get_prompt_template(self.prompt_name)

    def get_prompt(self) -> list[BaseMessage]:
        """
        Get a prompt from LangSmith hub if enabled, otherwise return fallback.
        """

        formatted_input = self._get_formatted_input()

        if self._is_langsmith_enabled():
            try:
                langsmith_prompt = pull_prompt(self.prompt_name)
                return (
                    langsmith_prompt.format_messages(**formatted_input)
                    if formatted_input
                    else langsmith_prompt.format_messages(**self.kwargs)
                )

            except Exception as e:
                logger.warning(
                    f"Failed to load LangSmith prompt "
                    f"'{self.prompt_name}': {e}. "
                    f"Using fallback prompt instead."
                )

                return self.prompt_selector.get_prompt(self.prompt_name, **self.kwargs)

        else:
            return self.prompt_selector.get_prompt(self.prompt_name, **self.kwargs)


def get_prompt(node_name: NodeName, **kwargs) -> list[BaseMessage]:
    return PromptManager(node_name, **kwargs).get_prompt()


def get_prompt_llm_chain(
    node_name: NodeName,
    config: RunnableConfig,
    *,
    schema=None,
    tool_names=None,
) -> Runnable:
    """
    Build a runnable chain that:
      - accepts raw variables as input
      - formats them into messages using the existing prompt manager
      - invokes the configured LLM

    This keeps the runnable input as the original variables.
    """

    prompt_template = PromptManager(node_name).get_prompt_template()

    def format_prompt(variables: dict | None) -> list[BaseMessage]:
        input_vars = variables or {}

        formatted_input = PromptSelector().format_prompt_input(node_name=node_name, **input_vars)

        if formatted_input:
            return prompt_template.invoke(formatted_input).to_messages()
        else:
            return prompt_template.invoke(input_vars).to_messages()

    formatter: Runnable = RunnableLambda(format_prompt).with_config(
        {"run_name": f"{node_name}_prompt_chain", "callbacks": []}
    )

    llm = get_configured_llm_for_node(
        node_name,
        config,
        tool_names=tool_names,
        schema=schema,
    )

    return formatter | llm
