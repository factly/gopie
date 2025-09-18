from langchain_core.messages import BaseMessage


def langsmith_compatible(content: str) -> str:
    """
    Convert content to be compatible with LangSmith by escaping curly braces.

    This function escapes single curly braces in the content to prevent them from being
    interpreted as template variables in LangSmith prompt templates.

    Args:
        content (str): The content string to make LangSmith compatible

    Returns:
        str: The content with curly braces escaped for LangSmith compatibility
    """
    return content.replace("{", "{{").replace("}", "}}")


def remove_double_curly_braces(messages: list[BaseMessage]) -> list[BaseMessage]:
    for msg in messages:
        if hasattr(msg, "content") and isinstance(msg.content, str):
            msg.content = msg.content.replace("{{", "{").replace("}}", "}")

    return messages
