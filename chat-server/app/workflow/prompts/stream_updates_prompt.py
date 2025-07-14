from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
)


def create_stream_update_prompt(**kwargs) -> list | ChatPromptTemplate:
    prompt_template = kwargs.get("prompt_template", False)
    original_user_query = kwargs.get("original_user_query", "")
    subquery_result = kwargs.get("subquery_result", "")
    subquery_messages = kwargs.get("subquery_messages", "")

    system_content = """
I need to create a brief update about the execution of a subquery.

INSTRUCTIONS:
1. First, determine if this subquery was successful or failed by examining
   the data.
2. If the subquery FAILED:
   - Never expose technical errors, stack traces, or system messages
   - Identify the issue in user-friendly terms (e.g., "couldn't find the requested information", "data not available")
   - Focus on what this means for the user's query rather than technical details
   - Analyze if this impacts the ability to answer the overall question
   - Clearly state if execution should continue or stop
   - Remain helpful and solution-oriented

3. If the subquery was SUCCESSFUL:
   - Provide a clear and concise summary of the results
   - Focus on the actual data retrieved and its relevance to the user's question
   - Highlight any interesting patterns or insights
   - Don't describe the execution process, focus on what was found

4. If the subquery returned TRUNCATED RESULTS:
   - Acknowledge that this part returned a large dataset that was limited due to large result sizes
   - Note that the data is already displayed to the user for analysis
   - Continue with execution as this is not a failure

5. Keep your response concise (2-3 sentences)
6. End by stating the next action (continue to next subquery, stopping execution, etc.)

WHAT TO AVOID:
- Technical jargon, SQL errors, or system implementation details
- Exposing errors or execution failures
- Blame language about system or user mistakes

Your response should be informative, actionable, and user-friendly.
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


def create_execution_analysis_prompt(**kwargs) -> list | ChatPromptTemplate:
    prompt_template = kwargs.get("prompt_template", False)
    last_stream_message_content = kwargs.get("last_stream_message_content", "")

    system_content = """
Analyze this message about a subquery execution and determine if
further execution should continue.

Make a decision based on:
1. If the message explicitly states to continue or stop
2. If the message mentions or implies a critical failure
3. If the message indicates an error that prevents further processing
4. Whether the remaining subqueries can still provide value

Return a JSON object with:
{
    "continue_execution": true/false,
    "reasoning": "brief explanation"
}
"""

    human_template_str = """
Message: {last_stream_message_content}
"""

    if prompt_template:
        return ChatPromptTemplate.from_messages(
            [
                SystemMessage(content=system_content),
                HumanMessagePromptTemplate.from_template(human_template_str),
            ]
        )

    human_content = human_template_str.format(
        last_stream_message_content=last_stream_message_content
    )

    return [
        SystemMessage(content=system_content),
        HumanMessage(content=human_content),
    ]
