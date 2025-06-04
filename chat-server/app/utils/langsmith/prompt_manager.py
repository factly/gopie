from app.core.config import settings
from app.core.log import logger
from app.utils.langsmith.client import (
    extract_content_from_prompt_template,
    pull_prompt_from_hub,
)
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
    ) -> str:
        """
        Get a prompt from LangSmith hub if enabled, otherwise return fallback.
        Returns:
            LangSmith prompt template or formatted fallback prompt string
        """

        if self.is_langsmith_enabled():
            try:
                langsmith_prompt = pull_prompt_from_hub(langsmith_prompt_name)
                formatted_prompt = langsmith_prompt.format(*args, **kwargs)

                prompt_content = extract_content_from_prompt_template(
                    formatted_prompt
                )

                return prompt_content

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

    def get_fallback_prompt(self, node_name: NodeName, *args, **kwargs) -> str:
        return PromptSelector().get_prompt(node_name, *args, **kwargs)


def get_prompt(node_name: NodeName, *args, **kwargs) -> str:
    return PromptManager().get_prompt(node_name, *args, **kwargs)
