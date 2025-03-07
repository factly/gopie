import json
from typing import Dict, Any, List, Optional, Union
from langchain_core.output_parsers import JsonOutputParser
from src.lib.graph.types import AIMessage, ErrorMessage, State
from src.lib.config.langchain_config import lc

def generate_result(state: State) -> Dict[str, List[Any]]:
    """Generate results of the executed query."""
    print("aggregated result", state.get("query_result"))

    try:
        query_type = state.get("query_type", "")
        return (_handle_conversational_query(state)
                if query_type in ("conversational", "tool_only")
                else _handle_data_query(state))
    except Exception as e:
        return {
            "messages": [ErrorMessage.from_text(json.dumps({
                "error": "Critical error in result generation",
                "details": str(e)
            }))]
        }

def _handle_conversational_query(state: State) -> Dict[str, List[Any]]:
    """Handle conversational or tool-only queries"""
    user_query = state.get("subqueries", [])
    tool_results = state.get("tool_results", [])

    prompt = f"""
    User Query: "{user_query}"
    Available Context: {json.dumps(tool_results, indent=2) if tool_results else "No additional context available."}

    Instructions:
    - Incorporate tool results naturally if relevant
    - Preserve crucial information but present it clearly
    - Respond professionally and warmly
    - Keep response concise (3-5 sentences) unless detailed explanation needed
    - Focus on direct, helpful answers
    """

    return {
        "messages": [AIMessage(content=str(lc.llm.invoke(prompt).content))]
    }

def _handle_data_query(state: State) -> Dict[str, List[Any]]:
    """Handle data analysis queries"""
    message = state["messages"][-1] if state.get("messages") else None
    user_query = state.get("subqueries", [])
    query_result = state.get("query_result", [])

    if not query_result:
        return _handle_empty_results()

    query_executed = state.get("sql_query", _extract_executed_query(message))
    if isinstance(query_executed, dict) and "error" in query_executed:
        return {"messages": [ErrorMessage.from_text(json.dumps(query_executed))]}

    prompt = f"""
    Context:
    - Query: "{user_query}"
    - SQL: "{query_executed}"
    - Results: {json.dumps(query_result, indent=2)}

    Instructions:
        1. Provide direct, concise answers
        2. Present key insights first
        3. Format numbers properly (1,000,000, ₹, etc.)
        4. Include trends and patterns for financial/statistical data
        5. Use clear comparative language
        6. Only use facts from query results
    """

    return {
        "messages": [AIMessage(content=str(lc.llm.invoke(prompt).content))]
    }

def _handle_empty_results() -> Dict[str, List[Any]]:
    """Handle empty query results"""
    return {
        "messages": [AIMessage(content=(
            "I analyzed your query but couldn't find matching data. This could be because:\n"
            "- The data isn't in our current datasets\n"
            "- The query needs rephrasing\n"
            "- Specific filters might be excluding all results\n\n"
            "Could you try rephrasing your question or asking about a different aspect?"
        ))]
    }

def _extract_executed_query(message: Optional[Any]) -> Union[str, Dict[str, str]]:
    """Extract executed query from message content"""
    if not message:
        return ""

    try:
        content = message.content
        if isinstance(content, str):
            return JsonOutputParser().parse(content).get("query_executed", "")
        elif isinstance(content, dict):
            return content.get("query_executed", "")
        return ""
    except Exception as e:
        return {
            "error": "Could not process query results",
            "details": str(e)
        }