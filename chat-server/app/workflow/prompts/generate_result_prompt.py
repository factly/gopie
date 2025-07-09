from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
)

from app.models.query import QueryResult
from app.workflow.prompts.formatters.multi_query_result import (
    format_multi_query_result,
)


def create_generate_result_prompt(**kwargs) -> list | ChatPromptTemplate:
    prompt_template = kwargs.get("prompt_template", False)
    input_content = kwargs.get("input", "")

    system_content = """
You are generating the final response to a user query based on query execution results.

CORE PRINCIPLES:
- Answer directly and confidently based on available information
- Use a friendly, professional tone
- Never mention technical implementation details (SQL, error codes, processing steps)
- Never fabricate data or make assumptions beyond provided context
- Present information clearly with proper formatting

RESPONSE APPROACH BY QUERY TYPE:

1. DATA ANALYSIS QUERIES (when results contain data):
   - Lead with direct answer to the user's query
   - Present key insights and conclusions from the data
   - Use proper formatting: bullet points, number formatting (1,000,000), currency symbols
   - Highlight patterns and trends with their significance
   - Provide actionable recommendations when appropriate
   - Structure: Main findings → Supporting details → Additional insights → Implications

2. EMPTY/NO RESULTS QUERIES:
   - Clearly state that no matching data was found
   - Analyze why the query might not have returned results
   - Provide 2-3 specific alternative approaches
   - Suggest query modifications for better results
   - Be helpful and encouraging, not apologetic
   - Reference elements from their original query

3. CONVERSATIONAL QUERIES:
   - Provide direct answers based on available information
   - Integrate tool results naturally
   - Maintain conversational, helpful tone

CRITICAL LIMITATIONS AWARENESS:
- If query methodology appears flawed or insufficient, clearly state this limitation
- When data seems incomplete or approach inadequate, prioritize acknowledging limitations
- Do not present uncertain results as confident conclusions
- If you cannot reliably answer due to data/methodology issues, state this clearly

WHAT TO AVOID:
- Technical jargon, SQL queries, or error messages
- Phrases like "based on the data" excessively
- Excessive apologies
- Making up non-existent data
- Showing processing details or implementation steps

FORMATTING:
- Use bullet points for multiple pieces of information
- Highlight most important information first
- Group related information together
- Use subheadings for complex information when needed
"""

    human_template_str = """
    {input}
"""

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


def format_generate_result_input(query_result: QueryResult) -> dict:
    input_str = format_multi_query_result(query_result)

    return {
        "input": input_str,
    }
