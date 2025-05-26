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
        You are a data query classifier. Your job is to categorize the user
        query into ONE of three types. You MUST prevent hallucination and only
        answer based on available context and data.

        USER QUERY: "{user_query}"

        PREVIOUS TOOL RESULTS: {json.dumps(tool_results, indent=2)}

        QUERY TYPES - Select exactly ONE:

        1. "data_query" - Requires SQL execution on datasets or data analysis
        * Needs database access to answer with actual data
        * Examples: "Show sales trends", "Calculate average temps by region",
          "Where were elections held last year"
        * Keywords: analyze, calculate, compare, find, show data, trends,
          statistics, reports
        * Use this when the query asks for specific data that needs to be
          retrieved from databases

        2. "conversational" - ONLY for queries that can be answered with
           available context OR when clarification is needed
        * Use ONLY when:
          a) Simple greetings or general questions about capabilities:
             "Hello", "What can you do?"
          b) Questions that can be answered from provided context/previous
             conversation
          c) When you need clarification from the user to properly answer
             their query
        * NEVER use for queries asking about specific facts, events, or data
          you don't have context for
        * If you don't have context about what the user is asking, classify
          as "data_query" instead
        * If you need clarification, provide specific questions about what
          information you need

        3. "tool_only" - Can be answered by calling available tools
        * Use ONLY when you are CONFIDENT that available tools will
          provide the complete answer
        * The tools must be able to provide sufficient information to fully
          answer the user's question
        * After getting tool results, the query may be reclassified to
          "conversational" or "data_query" or if more tool calls are needed
          than call the tools again.

        CRITICAL ANTI-HALLUCINATION GUIDELINES:
        - NEVER classify queries about specific facts/events you don't have
          context for as "conversational"
        - If you don't have information about what the user is asking,
          classify as "data_query"
        - Only use "conversational" when you can provide accurate answers
          from available context
        - If unsure between classifications, ALWAYS default to "data_query"
        - For "tool_only", be absolutely certain the tools can provide the
          complete answer

        CLARIFICATION HANDLING:
        - If the query is ambiguous and you need clarification, classify as
          "conversational"
        - In reasoning, specify exactly what clarification you need
        - Example: "I need clarification on which year you mean by 'last year'
          and which country's elections"

        DECISION PRIORITY (in order):
        1. If you need clarification → "conversational"
        2. If tools can definitely answer completely → "tool_only"
        3. If requires data analysis or you're unsure → "data_query"
        4. If answerable from available context → "conversational"

        FORMAT YOUR RESPONSE AS JSON:
        {{
            "query_type": "data_query" OR "conversational" OR "tool_only",
            "reasoning": "Clear explanation of your classification decision and
                         what information you have or need",
            "clarification_needed": "If conversational due to needing
                                    clarification, specify what you need to
                                    know"
        }}
    """
