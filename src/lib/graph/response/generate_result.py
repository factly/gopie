import json
from typing import Dict, Any, List, Optional, Union
from langchain_core.output_parsers import JsonOutputParser
from src.lib.graph.types import AIMessage, ErrorMessage, State
from src.lib.config.langchain_config import lc


def generate_result(state: State) -> Dict[str, List[Any]]:
    """
    Generate results of the executed query for successful cases.
    Returns:
        Dictionary with messages containing the generated response
    """
    try:
        query_type = state.get("query_type", "")

        if query_type == "conversational" or query_type == "tool_only":
            return _handle_conversational_query(state)

        return _handle_data_query(state)

    except Exception as e:
        return {
            "messages": [ErrorMessage.from_text(json.dumps({
                "error": "Critical error in result generation",
                "details": str(e)
            }))]
        }


def _handle_conversational_query(state: State) -> Dict[str, List[Any]]:
    """Handle conversational or tool-only queries"""
    user_query = state.get("user_query", "")
    tool_results = state.get("tool_results", [])

    conversational_prompt = f"""
    # User Query Analysis

    ## User Message
    "{user_query}"

    ## Available Context Information
    {json.dumps(tool_results, indent=2) if tool_results else "No additional context available."}

    ## Instructions
        - This is a conversational query rather than a data analysis request.
        - If the tool results provide relevant information, incorporate it naturally into your response.
        - Preserve any crucial information from the tool results but present it in a clear, user-friendly way.
        - If answering a greeting, respond warmly and professionally.
        - If the user asks about capabilities, explain your data analysis features briefly.
        - Maintain a helpful, informative tone throughout.
        - Keep your response concise (3-5 sentences if possible) unless detailed explanation is needed.
    """

    response = lc.llm.invoke(conversational_prompt)
    return {
        "messages": [AIMessage(content=str(response.content))]
    }


def _handle_data_query(state: State) -> Dict[str, List[Any]]:
    """Handle data analysis queries with query results"""
    message = state["messages"][-1] if state.get("messages") else None
    user_query = state.get("user_query", "")
    query_result = state.get("query_result", [])

    if not query_result:
        return _handle_empty_results()

    query_executed = state.get("sql_query", _extract_executed_query(message))

    if isinstance(query_executed, dict) and "error" in query_executed:
        return {"messages": [ErrorMessage.from_text(json.dumps(query_executed))]}

    analysis_prompt = f"""
    # Data Analysis Response Generation

    ## Context
        - Original user query: "{user_query}"
        - Executed query: "{query_executed}"
        - Query results: {json.dumps(query_result, indent=2)}

    ## Response Instructions
        1. Provide a direct, concise answer addressing the user's specific question.
        2. Structure your response with key insights first, followed by supporting details.
        3. Include precise numerical data from the results with proper formatting:
        - Format large numbers with commas (e.g., 1,000,000)
        - Include currency symbols where appropriate (₹, $, etc.)
        - Use consistent decimal precision
        4. If presenting financial or statistical data, provide brief context about trends or patterns.
        5. If comparing multiple items, consider using clear comparative language.
        6. CRITICAL: Only use facts directly supported by the data in the query results.
        7. Do not apologize for or mention limitations of your analysis.

        Respond in a professional, authoritative tone appropriate for data analysis.
    """

    response = lc.llm.invoke(analysis_prompt)
    return {
        "messages": [AIMessage(content=str(response.content))]
    }


def _handle_empty_results() -> Dict[str, List[Any]]:
    """Handle the case of empty query results"""
    return {
        "messages": [AIMessage(content=(
            "I analyzed your query but couldn't find matching data in the available datasets. "
            "This could be because:\n"
            "- The data you're looking for isn't in our current datasets\n"
            "- Your query might need to be rephrased\n"
            "- There might be specific filters that are excluding all results\n\n"
            "Could you try rephrasing your question or asking about a different aspect of the data?"
        ))]
    }

def _extract_executed_query(message: Optional[Any]) -> Union[str, Dict[str, str]]:
    """
    Extract the executed query from the message content

    Returns:
        Either the query string or an error dictionary
    """
    if not message:
        return ""

    try:
        message_content = message.content

        if isinstance(message_content, str):
            parser = JsonOutputParser()
            content = parser.parse(message_content)
        elif isinstance(message_content, dict):
            content = message_content
        else:
            content = {}

        return content.get("query_executed", "")
    except Exception as e:
        return {
            "error": "Could not process query results",
            "details": str(e)
        }