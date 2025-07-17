from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
)

from app.models.query import QueryResult
from app.workflow.prompts.formatters.format_query_result import format_query_result


def create_result_generation_prompt(**kwargs) -> list[BaseMessage] | ChatPromptTemplate:
    prompt_template = kwargs.get("prompt_template", False)
    input_content = kwargs.get("input", "")

    system_content = """
You are generating the final response to a user query based on the context provided.

CORE PRINCIPLES:
- Answer directly and confidently based on available information
- Use a friendly, professional tone
- Present information clearly with proper formatting
- Consider multiple subqueries in the context when answering the original user query

RESPONSE APPROACH BY QUERY TYPE:

1. DATA ANALYSIS QUERIES:
   - Lead with direct answer to the user's query
   - If the data is not enough to answer the user query, try to answer as much as possible and provide a helpful response to the user query for the missing data
   - Present key insights and conclusions from the data
   - Highlight patterns and trends with their significance
   - Provide actionable recommendations when appropriate
   - Structure: Main findings → Supporting details → Additional insights → Implications

2. TRUNCATED RESULTS:
   - Acknowledge that some SQL queries returned truncated results due to large result sizes
   - Note that the visible data from these queries can still be analyzed by the user
   - Offer to help with specific questions about the displayed data
   - Suggest filtering or refining the query for more focused results
   - Do not attempt to provide insights or conclusions from truncated query results

3. EMPTY/NO RESULTS QUERIES:
   - Clearly state that no matching data was found
   - Analyze why the query might not have returned results based on the context provided
   - Provide specific alternative approaches
   - Be helpful and encouraging, not apologetic

4. CONVERSATIONAL QUERIES:
   - Provide direct answers based on available information
   - Integrate tool results naturally
   - Maintain conversational, helpful tone

5. ERROR/PROBLEM QUERIES:
   - Identify the likely cause in user-friendly terms (e.g., "dataset doesn't contain the information needed")
   - Suggest specific alternative approaches or clarifications
   - Guide users toward successful query reformulation
   - Explain what type of data or context would be needed
   - Remain helpful and solution-oriented

QUALITY CONTROL:
- If query methodology appears flawed or insufficient, clearly state this limitation
- When data seems incomplete, not relevant to the user query or approach inadequate, prioritize acknowledging limitations
- Do not present uncertain results as confident conclusions
- If you cannot reliably answer due to data/methodology issues, state this clearly
- When errors occur, focus on what the user needs rather than what went wrong technically

FORMATTING:
- Use bullet points for multiple pieces of information
- Highlight most important information first
- Group related information together
- Use subheadings for complex information when needed

WHAT TO AVOID:
- Technical jargon, SQL queries, error messages, or system implementation details
- Excessive apologies or phrases like "based on the data"
- Making up non-existent data or assumptions beyond provided context
- Showing processing details or implementation steps
- Blame language about system failures or user mistakes
"""

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


def format_result_generation_input(query_result: QueryResult | None, **kwargs) -> dict:
    input_str = ""

    if not query_result:
        input_str = "No query result available for response generation."
    elif isinstance(query_result, QueryResult):
        input_str = format_query_result(query_result)

    return {"input": input_str}
