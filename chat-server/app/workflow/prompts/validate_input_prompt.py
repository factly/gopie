from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
)


def create_validate_input_prompt(
    **kwargs,
) -> list[BaseMessage] | ChatPromptTemplate:
    prompt_template = kwargs.get("prompt_template", False)
    user_input = kwargs.get("user_input", "")

    system_content = """\
Validate the user input

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
                SystemMessage(content=system_content),
                HumanMessagePromptTemplate.from_template(human_template_str),
            ]
        )

    human_content = human_template_str.format(input=user_input)

    return [
        SystemMessage(content=system_content),
        HumanMessage(content=human_content),
    ]
