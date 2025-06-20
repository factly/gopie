from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage


def create_response_prompt(
    user_query: str, dataset_name: str, data_context: str, **kwargs
) -> list[BaseMessage]:
    system_message = SystemMessage(
        content="""You are a helpful data analyst. Provide clear, helpful
responses based on the available data. Be conversational and focus on insights.

GUIDELINES:
- Base your response ONLY on the data provided
- Do not add information that isn't present in the results
- Be conversational and engaging
- Focus on key insights and patterns in the data
- Explain findings in simple, understandable terms"""
    )

    human_input = f"""Please answer this question: "{user_query}"

Dataset: {dataset_name}

Available Data:
{data_context}"""

    human_message = HumanMessage(content=human_input)

    return [system_message, human_message]
