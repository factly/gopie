from langchain_core.messages import BaseMessage

from app.core.config import settings
from app.core.log import logger
from app.utils.langsmith.client import pull_prompt
from app.workflow.prompts.prompt_selector import NodeName, PromptSelector


class PromptManager:
    """
    Manages prompt retrieval from LangSmith with fallback support.
    """

    def is_langsmith_enabled(self) -> bool:
        return settings.LANGSMITH_PROMPT

    def get_prompt(
        self,
        langsmith_prompt_name: NodeName,
        *args,
        **kwargs,
    ) -> list[BaseMessage] | str:
        """
        Get a prompt from LangSmith hub if enabled, otherwise return fallback.
        Returns:
            LangSmith prompt template or formatted fallback prompt string
        """

        formatted_input = PromptSelector().format_prompt_input(
            langsmith_prompt_name, *args, **kwargs
        )

        if self.is_langsmith_enabled():
            try:
                langsmith_prompt = pull_prompt(langsmith_prompt_name)

                if formatted_input:
                    formatted_prompt = langsmith_prompt.format_messages(
                        **formatted_input
                    )
                else:
                    formatted_prompt = langsmith_prompt.format_messages(
                        *args, **kwargs
                    )

                return formatted_prompt

            except Exception as e:
                logger.warning(
                    f"Failed to load LangSmith prompt "
                    f"'{langsmith_prompt_name}': {e}. "
                    f"Using fallback prompt instead."
                )

                return self.get_fallback_prompt(
                    langsmith_prompt_name, *args, **kwargs
                )

        else:
            return self.get_fallback_prompt(
                langsmith_prompt_name, *args, **kwargs
            )

    def get_fallback_prompt(
        self, node_name: NodeName, *args, **kwargs
    ) -> list[BaseMessage] | str:
        return PromptSelector().get_prompt(node_name, *args, **kwargs)


def get_prompt(
    node_name: NodeName, *args, **kwargs
) -> list[BaseMessage] | str:
    input_messages = PromptManager().get_prompt(node_name, *args, **kwargs)
    return input_messages
