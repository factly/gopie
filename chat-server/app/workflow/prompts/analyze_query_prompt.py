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
        You are a data query classifier. Categorize the user query into ONE
        of three types. Prevent hallucination - only answer based on available
        context and data.

        USER QUERY: "{user_query}"
        PREVIOUS TOOL RESULTS: {json.dumps(tool_results, indent=2)}

        QUERY TYPES - Select exactly ONE:

        1. "data_query" - Requires database access or data analysis
        * Examples: "Show sales trends", "Where were elections held last year"
        * Use when asking for specific data that needs database retrieval
        * Default choice when unsure between classifications

        2. "conversational" - Answerable with available context OR extremely
           vague queries needing clarification
        * Use ONLY for:
          a) Greetings: "Hello", "What can you do?"
          b) Questions answerable from provided context/previous conversation
          c) Extremely vague queries where no reasonable assumptions possible
        * NEVER use for specific facts/events without available context
        * Avoid clarification unless query is extremely vague

        3. "tool_only" - Definitively answerable by calling available tools
        * Use when confident tools provide complete answer
        * Tools must fully answer the user's question
        * May be reclassified after getting tool results

        CORE RULES:
        - Unknown facts/events → "data_query" (never "conversational")
        - When unsure → "data_query"
        - Clarification only for extremely vague queries
        - Let data retrieval handle specific filtering

        DECISION PRIORITY:
        1. Tools can answer completely → "tool_only"
        2. Needs data/unsure → "data_query"
        3. Available context → "conversational"
        4. Extremely vague → "conversational" with clarification

        FORMAT YOUR RESPONSE AS JSON:
        {{
            "query_type": "data_query" OR "conversational" OR "tool_only",
            "reasoning": "Brief explanation of classification decision",
            "clarification_needed": "If conversational due to vagueness,
                                    specify what you need"
        }}
    """
