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
        You are an AI assistant specialized in data analysis.
        Your role is to help users analyze data by determining query types.

        USER QUERY:
        "{user_query}"

        TOOL RESULTS from previous tool calls:
        {json.dumps(tool_results)}

        INSTRUCTIONS:
        1. Classify this query into ONE of these types:
            - "data_query": Requires SQL execution on datasets
            (e.g., analysis, trends, statistics, filtered data)
            - "conversational": General conversation not requiring
                                data or tools
            - "tool_only": Can be answered using available tools without SQL

        2. For data queries:
            - These require accessing and analyzing datasets with SQL
            - Examples: "Show me sales trends",
              "What's the average price?", "Compare metrics across regions"

        3. For conversational queries:
            - General questions, greetings, or casual conversation
            - No dataset analysis or tools required

        4. For tool-only queries:
            - If the query can be answered directly with
              tool calls without dataset analysis, make those tool calls
            - Try to call all necessary tools at once to answer the query
            - Can be answered with tools but don't require SQL processing
            - Examples: Questions about available datasets, \
              schema information, metadata, tool-specific questions or can be
              answered with the available tools

        If there is a need of calling a tool to answer the query,
        please call the tool(s) and dont return in the requested format
        and directly make a tool call

        Response format:
        {{
            "query_type": "data_query|conversational|tool_only",
            "reasoning": "Clear explanation of classification decision",
            "data_query": true|false,
        }}
    """
