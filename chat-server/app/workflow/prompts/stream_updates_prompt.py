def create_stream_update_prompt(
    query_text: str,
    subquery_count: int,
    original_user_query: str,
    query_index: int,
    subquery_result: str,
    error_message: str,
    sql_queries: str,
    node_messages: str,
    remaining_subqueries: str,
) -> str:
    """
    Create a prompt for generating stream updates about subquery execution.

    Args:
        query_result: The overall query result object
        query_index: The current subquery index
        subquery_result: The specific subquery result
        sql_queries: List of SQL queries used
        node_messages: Messages from the node execution
        remaining_subqueries: List of remaining subqueries

    Returns:
        A formatted prompt string for stream updates
    """

    prompt = f"""
I need to create a brief update about the execution of a subquery.

Original User Query: "{original_user_query}"

This is subquery {query_index} / {subquery_count}:
"{query_text}"

SQL Queries Used:
{sql_queries}

Subquery Result Information:
{subquery_result}

Node Messages:
{node_messages}

Error Information (if any):
{error_message}

Remaining Subqueries:
{remaining_subqueries}

INSTRUCTIONS:
1. First, determine if this subquery was successful or failed by examining
   the data.
2. If the subquery FAILED:
   - Explain in simple terms why it failed
   - Analyze if this failure is critical for the remaining subqueries
   - Clearly state if execution should continue or stop
   - Be professional but empathetic about the failure

3. If the subquery was SUCCESSFUL:
   - Provide a clear and concise summary of the results
   - Focus on the actual data retrieved and its relevance to the user's
     question
   - Highlight any interesting patterns or insights
   - Don't describe the execution process, focus on what was found

4. Keep your response concise (2-3 sentences)
5. End by stating the next action (continue to next subquery, stopping
   execution, etc.)

Your response should be informative, actionable, and user-friendly.
"""

    return prompt


def create_execution_analysis_prompt(last_stream_message_content: str) -> str:
    """
    Create a prompt for analyzing whether further execution should continue.

    Args:
        last_stream_message_content: Content of the last stream message

    Returns:
        A formatted prompt string for execution analysis
    """

    prompt = f"""
Analyze this message about a subquery execution and determine if
further execution should continue.

Message: {last_stream_message_content}

Make a decision based on:
1. If the message explicitly states to continue or stop
2. If the message mentions or implies a critical failure
3. If the message indicates an error that prevents further processing
4. Whether the remaining subqueries can still provide value

Return a JSON object with:
{{
    "continue_execution": true/false,
    "reasoning": "brief explanation"
}}
"""

    return prompt
