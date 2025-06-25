from langchain_core.messages import HumanMessage, SystemMessage


def create_route_query_replan_prompt(
    last_message_content: str | list,
    subquery_errors: list | None,
    node_messages: dict,
) -> list:
    system_content = """
You are a query execution error analyzer. Your task is to analyze SQL execution errors and determine the best next action for query processing.

ANALYSIS INSTRUCTIONS:
Analyze all available information carefully to determine the best next action.
Consider the nature of the error, the execution context in node_messages,
and what previous attempts have revealed.

AVAILABLE OPTIONS:

1. "reidentify_datasets"
   Choose this when the underlying dataset structure doesn't match what was
   expected

2. "replan"
   Choose this when the query itself needs reformulation but the dataset
   understanding is correct

3. "validate_query_result"
   Choose this when either:
   - The current results are sufficient despite the error
   - Further retries would be futile
   - The error is expected and doesn't prevent moving forward
   - Analyzing the data and found that the error is not fixable by retrying
     the query

IMPORTANT NOTES:
- "validate_query_result" doesn't mean success - it means we proceed with
  what we have
- Avoid making simplistic decisions based solely on error keywords
- Synthesize all available context to determine the most appropriate action

RESPONSE FORMAT:
Return ONLY one of these exact strings: "reidentify_datasets", "replan", or
"validate_query_result"
"""

    content_str = (
        str(last_message_content)
        if isinstance(last_message_content, list)
        else last_message_content
    )

    errors_str = (
        str(subquery_errors) if subquery_errors else "No previous errors"
    )

    human_content = f"""
I encountered an error when executing the SQL query:
{content_str}

Previous error messages (including current attempt):
{errors_str}

Node execution messages and context:
{node_messages}
"""

    return [
        SystemMessage(content=system_content),
        HumanMessage(content=human_content),
    ]
