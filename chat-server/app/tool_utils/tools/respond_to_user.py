from typing import Literal

from langchain_core.tools import tool


@tool
def respond_to_user(
    query_type: Literal["conversational", "data_query"],
    confidence_score: int,
    reasoning: str,
    clarification_needed: str | None,
    status_message: str,
    response_data: str | None,
):
    """
    Respond to the user with query classification results and any gathered data.

    This tool is called as the final step in the query analysis workflow to return
    the classification decision and any relevant information to the user. For
    conversational queries, it includes data collected from tool calls. For data
    queries, it signals handoff to the full processing workflow.

    Args:
        query_type (str): Classification type - either "conversational" (handle
            directly with available tools) or "data_query" (hand off to full
            workflow for complex processing).
        confidence_score (int): Confidence level from 1-10.
            - 8-10 (High): Clear simple metadata or obvious complex analytical queries
            - 4-7 (Medium): Ambiguous queries that could benefit from exploration
            - 1-3 (Low): Uncertain queries needing more context
        reasoning (str): Brief explanation of the classification decision,
            including complexity assessment (e.g., "Simple metadata query - can
            be handled with available tools").
        clarification_needed (str): If the query is vague, specify what additional
            information is needed from the user. Set to null if no clarification
            is required.
        status_message (str): User-friendly response or next steps message.
            Must be 120 characters or less.
        response_data (str): Any data collected from tool calls or context for
            conversational queries. Set to null for data_query handoffs.
    """
    return {
        "query_type": query_type,
        "confidence_score": confidence_score,
        "reasoning": reasoning,
        "clarification_needed": clarification_needed,
        "status_message": status_message,
        "response_data": response_data,
    }


__tool__ = respond_to_user
__tool_category__ = "Query Analysis"
__should_display_tool__ = False
