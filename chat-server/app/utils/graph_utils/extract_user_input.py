from app.models.router import Message


def extract_user_input(messages: list[Message]):
    if messages[-1].role == "user":
        user_input = str(messages[-1].content)
    else:
        raise Exception("Last Message must be a user message")

    if user_input == "":
        raise Exception("Last Message cannot be empty")

    return user_input
