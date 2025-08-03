from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
)


def create_stream_update_prompt(**kwargs) -> list | ChatPromptTemplate:
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
You need to analyze the subquery execution and provide both a user-friendly update AND decide if execution should continue.

FOR THE STREAM UPDATE MESSAGE:
1. First, determine if this subquery was successful or failed by examining the data.
2. If the subquery FAILED:
   - Never expose technical errors, stack traces, or system messages
   - Identify the issue in user-friendly terms (e.g., "couldn't find the requested information", "data not available")
   - Focus on what this means for the user's query rather than technical details
3. If the subquery was SUCCESSFUL:
   - Provide a clear and concise summary of the results
   - Focus on the actual data retrieved and its relevance to the user's question
   - Highlight any interesting patterns or insights
4. If the subquery returned TRUNCATED RESULTS:
   - Acknowledge that this part returned a large dataset that was limited due to large result sizes
   - Note that the data is already displayed to the user for analysis
5. Keep your response concise (2-3 sentences)
6. If the query is asking for visualizations, do not mention it as it is out of scope for you to answer.

FOR THE EXECUTION DECISION:
1. Set continue_execution to false if:
   - The subquery failed critically and prevents further processing
   - The current results already provide sufficient information to answer the user's query
   - There's an error that would affect remaining subqueries
2. Set continue_execution to true if:
   - The subquery was successful and more data is needed
   - The failure doesn't prevent other subqueries from running
   - Additional subqueries would provide valuable context

WHAT TO AVOID:
- Technical jargon, SQL errors, or system implementation details
- Exposing errors or execution failures
- Blame language about system or user mistakes
"""

    human_template_str = """
Original User Query: "{original_user_query}"

{subquery_messages}

Subquery Result Information:
{subquery_result}
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
