from langchain_core.messages import BaseMessage, HumanMessage


def extract_user_input(messages: list[BaseMessage]) -> str:
    """
    Extracts and returns the content of the last user message from a list of Message objects.

    Raises an exception if the last message is not from a user or if its content is empty.

    Parameters:
        messages (list[BaseMessage]): List of BaseMessage objects, where the last message is
        expected to be from a user.

    Returns:
        str: The content of the last user message.
    """
    if isinstance(messages[-1], HumanMessage):
        user_input = str(messages[-1].content)
    else:
        raise Exception("Last Message must be a user message")

    if not user_input:
        raise Exception("Last Message cannot be empty")

    return user_input
