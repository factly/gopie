from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
)


def create_validate_match_relevance_prompt(**kwargs) -> list[BaseMessage] | ChatPromptTemplate:
    prompt_template = kwargs.get("prompt_template", False)
    input_content = kwargs.get("input", "")

    system_message = """
You are an expert at evaluating semantic similarity between search terms and matched database values.

You will receive multiple fuzzy matches that were found using Levenshtein distance (approximate string matching). Your task is to validate ALL of them in one response:

For EACH fuzzy match, you must:
1. Evaluate if the matched values are semantically relevant to what the user was searching for
2. Consider the user's query context and the dataset/column being searched
3. Assign a relevance score (0-100):
   - 90-100: Perfect match, exactly what user meant
   - 70-89: Good match, clearly relevant to user's intent
   - 50-69: Partial match, somewhat relevant but may not be what user wanted
   - 0-49: Poor match, not what user was looking for

4. Mark as relevant (is_relevant=true) if score >= 70
5. If relevant, return the top 3 most relevant values from the matched list
6. If not relevant (score < 70), return empty relevant_values list

IMPORTANT: You must provide a validation result for EVERY match in the input list."""

    human_template_str = """
{input}
"""

    if prompt_template:
        return ChatPromptTemplate.from_messages(
            [
                SystemMessage(content=system_message),
                HumanMessagePromptTemplate.from_template(human_template_str),
            ]
        )

    human_content = human_template_str.format(input=input_content)

    return [
        SystemMessage(content=system_message),
        HumanMessage(content=human_content),
    ]
