import json


def create_conversational_query_prompt(user_query: str, query_result) -> str:
    """
    Create a prompt for handling conversational or tool-only queries.

    Args:
        user_query: The original user query
        query_result: The query result object

    Returns:
        A formatted prompt string for conversational queries
    """

    prompt = f"""
You are generating the final response to a user query.
This is the LAST step in the workflow.

USER QUERY: "{user_query}"

QUERY RESULT:
{json.dumps(query_result.to_dict(), indent=2)}

RESPONSE INSTRUCTIONS:
1. Answer the query directly and confidently based on all available
   information
2. Do not mention how you processed the information or your sources
3. Use a friendly, professional tone as if speaking directly to the user
4. Seamlessly integrate all relevant information from the available context
5. Use bullet points or numbered lists when presenting multiple pieces of
   information
6. Highlight the most important or directly relevant information first
7. If the query could not be fully answered, clearly explain what
   information is available and what might be missing
8. NEVER fabricate data or make assumptions beyond what's provided in the
   context
9. If you encounter contradictory information, acknowledge it and provide
   the most reliable interpretation based on the available evidence
10. Format your response for maximum readability
11. NEVER mention technical implementation details such as SQL queries,
    error codes, or processing steps
"""

    return prompt


def create_data_query_prompt(user_query: str, query_result) -> str:
    """
    Create a prompt for handling data analysis queries.

    Args:
        user_query: The original user query
        query_result: The query result object

    Returns:
        A formatted prompt string for data queries
    """

    prompt = f"""
You are generating the final response to a data analysis query.
This is the LAST step in the workflow.

USER QUERY: "{user_query}"

QUERY RESULT:
{json.dumps(query_result.to_dict(), indent=2)}

RESPONSE INSTRUCTIONS:
1. Begin with a direct, confident answer to the user's query
2. Focus on presenting insights and conclusions from the data, not the
   process
3. Structure your response in a logical flow:
   - Main findings and direct answer to the query
   - Supporting details and evidence from the data
   - Any additional insights or patterns discovered
   - Implications or actionable recommendations (if appropriate)

4. For numerical data:
   - Format properly with appropriate separators (e.g., 1,000,000)
   - Use currency symbols when relevant
   - Present percentages with appropriate precision

5. When presenting complex information:
   - Use bullet points or numbered lists for clarity
   - Group related information together
   - Use brief, descriptive subheadings if needed

6. If the data reveals patterns or trends:
   - Highlight these clearly
   - Explain their significance in context
   - Avoid technical jargon when explaining their meaning

7. When data is incomplete or has limitations:
   - Acknowledge these limitations briefly without technical details
   - Focus on what CAN be concluded from the available data
   - Suggest alternative approaches if appropriate

8. IMPORTANT DON'Ts:
   - Do NOT mention SQL queries, data processing steps, or technical
     implementation
   - Do NOT use phrases like "based on the data" or "according to the
     results"
   - Do NOT fabricate data or draw conclusions beyond what the data
     supports
   - Do NOT include error messages or technical details

9. TONE:
   - Professional but conversational
   - Confident in presenting findings
   - Educational when explaining complex concepts
   - Neutral and objective when presenting facts
"""

    return prompt


def create_empty_results_prompt(user_query: str, query_result) -> str:
    """
    Create a prompt for handling empty query results.

    Args:
        user_query: The original user query
        query_result: The query result object

    Returns:
        A formatted prompt string for empty results
    """

    prompt = f"""
You are generating a response for a query that returned no results.
This is the LAST step in the workflow.

USER QUERY: "{user_query}"

QUERY RESULT:
{json.dumps(query_result.to_dict(), indent=2)}

RESPONSE INSTRUCTIONS:
1. Acknowledge that no matching data was found for their specific query
2. Begin with a clear, direct statement that addresses what the user was
   looking for
3. Analyze the execution details to understand where the process
   encountered issues
4. Provide a helpful, constructive response that offers:
   - A brief explanation of why their query might not have returned results
   - 2-3 specific alternative approaches they could try
   - Suggestions for modifying their query to get better results

5. Be empathetic but confident, maintaining a helpful tone
6. Avoid technical jargon and error details - focus on what the user can
   do next
7. Personalize your response by referencing elements of their original
   query
8. Frame alternatives as positive suggestions rather than focusing on
   what didn't work

9. DO NOT:
   - Apologize excessively
   - Show technical error messages or SQL queries
   - Make up data that doesn't exist
   - Use generic responses that don't address their specific query

10. End with an encouraging note that invites them to try a modified
    approach
"""

    return prompt
