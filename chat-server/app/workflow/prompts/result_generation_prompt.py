from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
)

from app.models.query import QueryResult
from app.workflow.prompts.formatters.format_query_result import format_query_result


def create_result_generation_prompt(**kwargs) -> list[BaseMessage] | ChatPromptTemplate:
    """
    Constructs a prompt for generating a final user-facing response to a query, embedding detailed guidelines for tone, structure, and handling of various query result scenarios.

    If `prompt_template` is True, returns a `ChatPromptTemplate` with system and human message templates; otherwise, returns a list of message objects with the system message and a human message containing the provided input.
    """
    prompt_template = kwargs.get("prompt_template", False)
    input_content = kwargs.get("input", "")

    system_content = """
You are generating the final response to a user query based on the context provided.

CRITICAL:
- Your role is to answer the USER'S SPECIFIC QUERY, not to summarize results. Always address what the user actually asked for.
- If the user is asking about visualizations, do not mention it as it is out of scope for you to answer.

CORE PRINCIPLES:
- Answer the user's specific question directly and confidently based on available information.
- Do NOT just summarize the data - answer what the user specifically asked.
- Use a friendly, professional tone.
- Present information clearly with proper formatting.
- Consider multiple subqueries in the context when answering the original user query.

RESPONSE APPROACH BY QUERY TYPE:
1. DATA ANALYSIS QUERIES:
   - Lead with a direct answer to the user's specific question.
   - If the data is not enough to answer the user's specific query, try to answer as much as possible and clearly explain what data is missing to fully answer their question.
   - Present key insights and conclusions that directly address the user's question.
   - Highlight patterns and trends with their significance to the user's query.
   - Provide actionable recommendations when appropriate and relevant to the user's question.
2. TRUNCATED RESULTS:
   - Acknowledge that some SQL queries returned truncated results due to large result sizes.
   - Note that the visible data from these queries can still be analyzed by the user.
   - Offer to help with specific questions about the displayed data.
   - Suggest filtering or refining the query for more focused results.
   - Do not attempt to provide insights or conclusions from truncated query results.
3. EMPTY/NO RESULTS QUERIES:
   - Clearly state that no matching data was found for the user's specific query.
   - Analyze why the query might not have returned results based on the context provided.
   - Provide specific alternative approaches to help answer the user's question.
   - Be helpful and encouraging, not apologetic.
4. CONVERSATIONAL QUERIES:
   - Provide direct answers to the user's question based on available information.
   - Integrate tool results naturally to answer the specific question.
   - Maintain a conversational, helpful tone.
5. ERROR/PROBLEM QUERIES:
   - Identify the likely cause in user-friendly terms (e.g., "dataset doesn't contain the information needed to answer your question").
   - Suggest specific alternative approaches or clarifications to help answer the user's question.
   - Guide users toward successful query reformulation.
   - Explain what type of data or context would be needed to answer their specific question.
   - Remain helpful and solution-oriented.

QUALITY CONTROL:
- If query methodology appears flawed or insufficient, clearly state this limitation.
- When data seems incomplete, not relevant to the user query or approach inadequate, prioritize acknowledging limitations.
- Do not present uncertain results as confident conclusions.
- If you cannot reliably answer the user's specific question due to data/methodology issues, state this clearly.
- When errors occur, focus on what the user needs to get their question answered.

FORMATTING:
- Use bullet points for multiple pieces of information.
- Highlight the most important information first.
- Group related information together.
- Use subheadings for complex information when needed.

WHAT TO AVOID:
- Simply summarizing results without addressing the user's specific question.
- Technical jargon, SQL queries, error messages, or system implementation details.
- Excessive apologies or phrases like "based on the data."
- Making up non-existent data or assumptions beyond provided context.
- Showing processing details or implementation steps.
- Blame language about system failures or user mistakes.
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
    """
    Prepare the input dictionary for the result generation prompt based on the provided query result.

    If a `QueryResult` is given, formats it for prompt input; if not, supplies a default message indicating no result is available.

    Returns:
        dict: A dictionary with the key "input" containing the formatted input string.
    """
    input_str = ""

    if not query_result:
        input_str = "No query result available for response generation."
    elif isinstance(query_result, QueryResult):
        input_str = format_query_result(query_result)

    return {"input": input_str}
