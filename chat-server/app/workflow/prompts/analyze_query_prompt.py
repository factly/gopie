import json
from typing import Any, List


def create_analyze_query_prompt(
    user_query: str, tool_results: List[Any]
) -> str:
    """
    Create a prompt for analyzing a user query to determine its type.

    Args:
        user_query: The natural language query from the user
        tool_results: Results from any tools that were previously called

    Returns:
        A formatted prompt string
    """
    return f"""
        You are a data query classifier. Your only job is to categorize
        the user query into ONE of three types.

        USER QUERY: "{user_query}"

        PREVIOUS TOOL RESULTS: {json.dumps(tool_results, indent=2)}

        QUERY TYPES - Select exactly ONE:
        1. "data_query" - Requires SQL execution on datasets
        * Needs database access to answer
        * Examples: "Show sales trends", "Calculate average temps by region"
        * Keywords: analyze, calculate, compare, find, show data, trends

        2. "conversational" - General conversation not requiring data or tools
        * Simple questions, greetings, or casual conversation
        * Examples: "Hello", "How are you?", "What can you do?"
        * No data analysis or specialized tools needed

        3. "tool_only" - Can be answered by directly calling tools
        * Requires tools but NOT database queries
        * Directly call a tool to gather the required data for user answer
        * Examples: "What datasets do you have?", "Show schema for customers"
        * Keywords: available data, metadata, schema, help with

        CRITICAL GUIDELINES:
        - Choose EXACTLY ONE query type
        - If ANY part requires data analysis, classify as "data_query"
        - Be decisive - don't hedge or suggest multiple types
        - If tools can directly answer without SQL, classify as "tool_only"

        FORMAT YOUR RESPONSE AS JSON:
        {{
            "query_type": "data_query" OR "conversational" OR "tool_only",
            "reasoning": "1-2 sentences explaining your classification",
            "data_query": true OR false
        }}
    """
