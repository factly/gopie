from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
)

from app.models.query import QueryResult
from app.workflow.graph.single_dataset_graph.types import (
    SingleDatasetQueryResult,
)
from app.workflow.prompts.formatters.multi_query_result import format_multi_query_result
from app.workflow.prompts.formatters.single_query_result import format_single_query_result


def create_result_generation_prompt(**kwargs) -> list[BaseMessage] | ChatPromptTemplate:
    prompt_template = kwargs.get("prompt_template", False)
    input_content = kwargs.get("input", "")

    system_content = (
        """Just generate the result for the user query. Do not add any other information."""
    )

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


def format_result_generation_input(
    query_result: SingleDatasetQueryResult | QueryResult | None, **kwargs
) -> dict:
    if not query_result:
        return {"input": "No query result available for response generation."}

    if isinstance(query_result, QueryResult):
        input_str = format_multi_query_result(query_result)
    else:
        input_str = format_single_query_result(query_result)

    return {"input": input_str}
