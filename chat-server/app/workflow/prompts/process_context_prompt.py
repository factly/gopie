from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage


def create_process_context_prompt(
    current_query: str, chat_history: list, **kwargs
) -> list[BaseMessage]:
    system_content = """You are a context analyzer. Your task is to analyze the conversation history and current query to provide enhanced context for better data analysis.

Given the chat history and current query, you should:
1. Extract relevant context from previous messages that might help understand the current question
2. Enhance the current query by adding necessary context or making it more specific based on the conversation

Return your response as JSON with these fields:
- "enhanced_query": The refined version of the current query with better context
- "context_summary": A brief summary of relevant context from chat history (can be empty if no relevant context)

Be concise but thorough. Focus on information that would help a data analyst understand what the user is really asking for.

EXAMPLES:

Example 1:
Chat history: ["Show me sales data for 2023", "The total was $1.2M across all regions"]
Current query: "What about the trends?"
Enhanced query: "What are the sales trends for 2023 data that showed $1.2M total across all regions?"
Context summary: "User previously asked for 2023 sales data totaling $1.2M across regions"

Example 2:
Chat history: ["Tell me about covid cases", "India had 45M cases total"]
Current query: "Show me the vaccination data"
Enhanced query: "Show me vaccination data for India (previously discussed covid cases: 45M total)"
Context summary: "Previous discussion about India's covid cases (45M total)"

Example 3:
Chat history: []
Current query: "Show me the data"
Enhanced query: "Show me the data"
Context summary: ""
"""

    if chat_history and len(chat_history) > 0:
        formatted_history = []

        for msg in chat_history:
            if hasattr(msg, "content"):
                content = str(msg.content)
            else:
                content = str(msg)
            formatted_history.append(content)

        chat_summary = formatted_history
    else:
        chat_summary = ["No previous conversation"]

    human_content = f"""Current query: {current_query}

Chat history: {chat_summary}

Please analyze and enhance this query with relevant context."""

    return [
        SystemMessage(content=system_content),
        HumanMessage(content=human_content),
    ]
