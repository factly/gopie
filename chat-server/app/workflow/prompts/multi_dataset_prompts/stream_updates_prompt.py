from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
)


def create_stream_update_prompt(**kwargs) -> list[BaseMessage] | ChatPromptTemplate:
    """
    Generate a prompt for analyzing subquery execution and determining next steps in JSON format.

    Returns a structured JSON response with both stream update content and execution decision.

    Parameters:
        prompt_template (bool, optional): If True, returns a prompt template for dynamic use; otherwise, returns formatted messages.
        original_user_query (str, optional): The user's original query for context.
        subquery_result (str, optional): The result or output of the subquery.
        subquery_messages (str, optional): Additional messages or context related to the subquery.

    Returns:
        list | ChatPromptTemplate: Either a list of message objects or a prompt template, depending on the mode.
    """
    prompt_template = kwargs.get("prompt_template", False)
    original_user_query = kwargs.get("original_user_query", "")
    subquery_result = kwargs.get("subquery_result", "")
    subquery_messages = kwargs.get("subquery_messages", "")

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
ORIGINAL USER QUERY: "{original_user_query}"

SUBQUERY CONTEXT:
{subquery_messages}

SUBQUERY RESULT INFORMATION:
{subquery_result}

TASK: Analyze the above information and provide both a user-friendly update and execution decision.
"""

    if prompt_template:
        return ChatPromptTemplate.from_messages(
            [
                SystemMessage(content=system_content),
                HumanMessagePromptTemplate.from_template(human_template_str),
            ]
        )

    human_content = human_template_str.format(
        original_user_query=original_user_query,
        subquery_messages=subquery_messages,
        subquery_result=subquery_result,
    )

    return [
        SystemMessage(content=system_content),
        HumanMessage(content=human_content),
    ]
