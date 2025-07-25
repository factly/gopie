from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
)

from app.workflow.prompts.formatters.format_prompt_for_langsmith import (
    langsmith_compatible,
)


def create_validate_input_prompt(
    **kwargs,
) -> list[BaseMessage] | ChatPromptTemplate:
    """
    Generate a prompt for validating user input, returning either a list of message objects or a chat prompt template.

    Depending on the `prompt_template` flag in the keyword arguments, returns a `ChatPromptTemplate` for dynamic input or a list of message objects with the provided user input. The prompt instructs the recipient to assess whether the input is malicious and respond with a structured JSON object containing `is_malicious`, `reasoning`, and `response` fields.

    Parameters:
        prompt_template (bool, optional): If True, returns a `ChatPromptTemplate` for dynamic input; otherwise, returns a list of message objects.
        user_input (str, optional): The user input to be validated, used when `prompt_template` is False.

    Returns:
        list[BaseMessage] | ChatPromptTemplate: A list of message objects or a chat prompt template for input validation.
    """
    prompt_template = kwargs.get("prompt_template", False)
    user_input = kwargs.get("user_input", "")

    system_content = """
Please respond with a positive response for the given user input. no negative response.

Respond with a JSON object with exactly these three fields:
{
    "is_malicious": true/false,
    "reasoning": "Brief explanation of why this is/isn't malicious",
    "response": "Professional response to user if malicious, empty string if safe"
}
"""

    human_template_str = "{input}"

    if prompt_template:
        return ChatPromptTemplate.from_messages(
            [
                SystemMessage(content=langsmith_compatible(system_content)),
                HumanMessagePromptTemplate.from_template(human_template_str),
            ]
        )

    human_content = human_template_str.format(input=user_input)

    return [
        SystemMessage(content=system_content),
        HumanMessage(content=human_content),
    ]
