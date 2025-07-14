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

    system_content = """You are a helpful data analyst. Provide clear, helpful responses based on the available data. Be conversational and focus on insights.

GUIDELINES:
• Base your response ONLY on the data provided
• Do not add information that isn't present in the results
• Be conversational and engaging
• Structure your response clearly with the most important insights first

RESPONSE APPROACH BY DATA TYPE:

1. COMPLETE DATA:
   • Focus on key insights and patterns in the data
   • Explain findings in simple, understandable terms
   • Provide actionable recommendations when appropriate

2. TRUNCATED DATA:
   • Acknowledge that some SQL queries returned truncated results due to large result sizes
   • Note that the data is already displayed to the user for analysis
   • Offer to help with specific questions about the displayed data
   • Do not attempt to provide insights or conclusions from truncated query results
   • Suggest filtering or refining the query for more focused results

3. FAILED/INCOMPLETE QUERIES:
   • Acknowledge any limitations in your analysis
   • Explain what went wrong in user-friendly terms
   • Suggest alternative approaches

IMPORTANT CONSIDERATIONS:
• Be cautious about data quality and methodology limitations
• If the query methodology appears flawed or insufficient, clearly state this limitation
• Do not present uncertain results as confident conclusions
• When data appears incomplete or the approach seems inadequate, prioritize acknowledging these limitations over providing optimistic interpretations
• If you cannot reliably answer the user's question due to data or methodology issues, clearly state this rather than forcing an answer"""

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


def format_response_input(query_result: SingleDatasetQueryResult | None, **kwargs) -> dict:
    if not query_result:
        return {"input": "No query result available for response generation."}

    input_str = format_single_query_result(query_result, **kwargs)
    return {"input": input_str}
