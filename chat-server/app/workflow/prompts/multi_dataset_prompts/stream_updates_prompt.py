from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
)

from app.models.query import SubQueryInfo


def stream_update_prompt(**kwargs) -> list[BaseMessage] | ChatPromptTemplate:
    """
    Generate a prompt for analyzing subquery execution and determining next steps in JSON format.

    Returns a structured JSON response with both stream update content and execution decision.

    Parameters:
        prompt_template (bool, optional): If True, returns a prompt template for dynamic use; otherwise, returns formatted messages.
        input (str, optional): Formatted input from format_stream_update_input function.

    Returns:
        list | ChatPromptTemplate: Either a list of message objects or a prompt template, depending on the mode.
    """
    prompt_template = kwargs.get("prompt_template", False)
    input_content = kwargs.get("input", "")

    system_content = """
You are responsible for analyzing subquery execution results and providing both user-friendly
updates and execution continuation decisions.

STREAM UPDATE MESSAGE GUIDELINES:

1. EXECUTION STATUS ASSESSMENT:
   First determine if the subquery was successful or failed by examining the data

2. FAILURE HANDLING:
   - Never expose technical errors, stack traces, or system messages
   - Describe issues in user-friendly terms (e.g., "couldn't find requested information")
   - Focus on implications for the user's query rather than technical details

3. SUCCESS REPORTING:
   - Provide clear, concise summary of retrieved results
   - Focus on actual data retrieved and relevance to user's question
   - Highlight interesting patterns or insights discovered

4. TRUNCATED RESULTS:
   - Acknowledge when large datasets were limited due to size constraints
   - Note that complete data is displayed to the user for analysis

5. RESPONSE GUIDELINES:
   - Keep responses concise (2-3 sentences maximum)
   - Ignore visualization requests as they are handled separately

EXECUTION DECISION LOGIC:

SET continue_execution = FALSE when:
- Subquery failed critically and prevents further processing
- Current results provide sufficient information to answer user's query
- Errors would affect remaining subqueries

SET continue_execution = TRUE when:
- Subquery was successful and more data is needed
- Failure doesn't prevent other subqueries from running
- Additional subqueries would provide valuable context

CONTENT RESTRICTIONS:
- Avoid technical jargon, SQL errors, or system implementation details
- Never expose errors or execution failures to users
- Eliminate blame language about system or user mistakes
- Maintain professional, helpful tone throughout
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


def format_stream_update_input(
    subquery: SubQueryInfo,
    original_user_query: str,
    subquery_messages: str,
) -> dict:

    input_str = f'❓ ORIGINAL USER QUERY: "{original_user_query}"\n'

    input_str += f"\n📋 SUBQUERY CONTEXT:\n{subquery_messages}\n"

    input_str += "\n📊 SUBQUERY RESULT INFORMATION:\n"
    input_str += f"Query: {subquery.query_text}\n"

    if subquery.retry_count > 0:
        input_str += f"🔄 Retry Count: {subquery.retry_count}\n"

    if subquery.tables_used:
        input_str += f"📋 Tables: {subquery.tables_used}\n"

    if subquery.sql_queries:
        input_str += f"\n💾 SQL QUERIES EXECUTED ({len(subquery.sql_queries)}):\n"
        for j, sql_info in enumerate(subquery.sql_queries, 1):
            input_str += f"\n--- SQL Query {j} ---\n"
            input_str += f"Query: {sql_info.sql_query}\n"
            input_str += f"Explanation: {sql_info.explanation}\n"
            input_str += f"Success: {sql_info.success}\n"

            if sql_info.sql_query_result is not None:
                input_str += f"Result: {sql_info.sql_query_result}\n"
            else:
                input_str += "Result: No data returned\n"

            if not sql_info.success and sql_info.error:
                input_str += f"Error: {sql_info.error}\n"

    if subquery.non_sql_response:
        input_str += f"\n💬 Non SQL Response: {subquery.non_sql_response}\n"

    if subquery.error_message:
        input_str += "\n⚠️ ERRORS ENCOUNTERED:\n"
        for error in subquery.error_message:
            for error_type, error_msg in error.items():
                input_str += f"- {error_type}: {error_msg}\n"

    if subquery.node_messages:
        input_str += "\n🔍 ADDITIONAL CONTEXT:\n"
        for node, message in subquery.node_messages.items():
            input_str += f"- {node}: {message}\n"

    input_str += "\n🎯 TASK: Analyze the above information and provide both a user-friendly update and execution decision."

    return {"input": input_str}
