from langchain_core.messages import AIMessage, BaseMessage

from app.core.log import logger


def estimate_tokens(message: BaseMessage) -> int:
    content = str(message.content) if message.content else ""
    base_tokens = len(content) // 4  # ~4 characters per token

    # Add extra tokens for tool calls in AI messages
    if isinstance(message, AIMessage) and message.tool_calls:
        tool_tokens = sum(len(str(tool.get("args", {}))) // 4 + 10 for tool in message.tool_calls)
        return base_tokens + tool_tokens + 10

    return base_tokens + 5  # Base overhead


def apply_sliding_window(
    chat_history: list[BaseMessage], min_messages: int = 10, max_tokens: int = 8000
) -> list[BaseMessage]:
    """
    Apply token-aware sliding window to chat history with minimum message guarantee.

    Args:
        chat_history: List of chat messages
        min_messages: Minimum number of messages to keep (guaranteed)
        max_tokens: Maximum estimated token count (primary constraint)

    Returns:
        Filtered chat history

    Behavior:
        - Prioritizes token limit as primary constraint
        - Guarantees minimum number of messages (even if slightly over token limit)
        - Adds messages from most recent backwards based on available token space
        - Uses token budget efficiently
    """
    if not chat_history:
        return chat_history

    total_messages = len(chat_history)

    if total_messages <= min_messages:
        return chat_history

    total_tokens = sum(estimate_tokens(msg) for msg in chat_history)
    if total_tokens <= max_tokens:
        return chat_history

    logger.info(f"Applying token-aware sliding window: {total_messages} messages")

    filtered_messages = []
    current_tokens = 0

    # Step 1: First, secure minimum messages from the most recent ones
    for i in range(total_messages - 1, max(total_messages - min_messages - 1, -1), -1):
        message = chat_history[i]
        msg_tokens = estimate_tokens(message)
        filtered_messages.insert(0, message)
        current_tokens += msg_tokens

    # Step 2: If we're within token limit, try to add more older messages
    if current_tokens <= max_tokens:
        for i in range(total_messages - min_messages - 1, -1, -1):
            message = chat_history[i]
            msg_tokens = estimate_tokens(message)

            if current_tokens + msg_tokens <= max_tokens:
                filtered_messages.insert(0, message)
                current_tokens += msg_tokens
            else:
                break
    else:
        logger.warning(
            f"Minimum {min_messages} messages ({current_tokens} tokens) exceed limit ({max_tokens})"
        )

    final_count = len(filtered_messages)
    logger.info(
        f"Token-aware filtering: {total_messages} -> {final_count} messages, ~{current_tokens} tokens"
    )

    return filtered_messages
