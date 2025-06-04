from langchain import hub
from langsmith import Client


def get_langsmith_client():
    return Client()


def pull_prompt_from_hub(prompt_name: str):
    return hub.pull(prompt_name)


def extract_content_from_prompt_template(formatted_prompt) -> str:
    """
    Extract content from a chat prompt template.

    If multiple messages: return as-is
    If single message: return just the content

    Args:
        formatted_prompt: The formatted prompt from LangSmith

    Returns:
        The prompt content (string if single message, original if multiple)
    """
    return str(formatted_prompt)
