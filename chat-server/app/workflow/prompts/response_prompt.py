from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
)

from app.workflow.graph.single_dataset_graph.types import (
    SingleDatasetQueryResult,
)
from app.workflow.prompts.formatters.single_query_result import (
    format_single_query_result,
)


def create_response_prompt(**kwargs) -> list[BaseMessage] | ChatPromptTemplate:
    prompt_template = kwargs.get("prompt_template", False)
    input_content = kwargs.get("input", "")

    system_content = """You are a helpful data analyst. Provide clear, helpful
responses based on the available data. Be conversational and focus on insights.

GUIDELINES:
- Base your response ONLY on the data provided
- Do not add information that isn't present in the results
- Be conversational and engaging
- Focus on key insights and patterns in the data
- Explain findings in simple, understandable terms
- If there are failed queries, acknowledge any limitations in your analysis
- Structure your response clearly with the most important insights first"""

    human_template_str = "{input}"

    if prompt_template:
        return ChatPromptTemplate.from_messages(
            [
                SystemMessage(content=system_content),
                HumanMessagePromptTemplate.from_template(human_template_str),
            ]
        )

    human_content = human_template_str.format(input=input_content)

    return [
        SystemMessage(content=system_content),
        HumanMessage(content=human_content),
    ]


def format_response_input(
    query_result: SingleDatasetQueryResult, **kwargs
) -> dict:
    formatted_input = format_single_query_result(query_result)
    return {"input": formatted_input}
