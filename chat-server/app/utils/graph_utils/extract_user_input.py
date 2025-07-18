from app.models.router import Message


def extract_user_input(messages: list[Message]):
    """
    Extracts and returns the content of the last user message from a list of Message objects.
    
    Raises an exception if the last message is not from a user or if its content is empty.
    
    Parameters:
    	messages (list[Message]): List of Message objects, where the last message is expected to be from a user.
    
    Returns:
    	str: The content of the last user message.
    """
    if messages[-1].role == "user":
        user_input = str(messages[-1].content)
    else:
        raise Exception("Last Message must be a user message")

    if user_input == "":
        raise Exception("Last Message cannot be empty")

    return user_input
