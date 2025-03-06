from typing import Any
from src.lib.graph.types import State, IntermediateStep, ErrorMessage
import json
from langchain_core.messages import AIMessage
from langchain_core.output_parsers import JsonOutputParser
from src.lib.config.langchain_config import lc
from src.tools.tool_node import has_tool_calls

def create_llm_prompt(user_query: str, tool_results: list):
    """Create a prompt for the LLM to identify the query type"""

    return f"""
        You are an AI assistant specialized in data analysis. Your role is to help users analyze data by determining query types.

        USER QUERY:
        "{user_query}"

        TOOL RESULTS:
        {json.dumps(tool_results)}

        INSTRUCTIONS:
        1. Classify this query into ONE of these types:
            - "data_query": Requires SQL execution on datasets (e.g., analysis, trends, statistics, filtered data)
            - "conversational": General conversation not requiring data or tools
            - "tool_only": Can be answered using available tools without SQL

        2. For data queries:
            - These require accessing and analyzing datasets with SQL
            - Examples: "Show me sales trends", "What's the average price?", "Compare metrics across regions"

        3. For conversational queries:
            - General questions, greetings, or casual conversation
            - No dataset analysis or tools required

        4. For tool-only queries:
            - If the query can be answered directly with tool calls without dataset analysis, make those tool calls
            - Try to call all necessary tools at once to answer the query
            - Can be answered with tools but don't require SQL processing
            - Examples: Questions about available datasets, schema information, metadata, tool-specific questions or can be      answered with the available tools

        If there is a need of calling a tool to answer the query, please call the tool(s) and dont return in the requested format and directly make a tool call

        RESPONSE FORMAT:
        Respond in this JSON format:
        {{
            "query_type": "data_query|conversational|tool_only",
            "reasoning": "Clear explanation of classification decision",
            "data_query": true|false,
        }}
        """

def analyze_query(state: State) -> dict:
    """
    Analyze the user query and the identified datasets to determine:
    1. If this is a data query requiring dataset processing
    2. If this is a conversational query needing no datasets
    3. If this is a tool-only query that can be handled without SQL execution

    Args:
        state: The current state object containing messages and tool results

    Returns:
        Query type and call tools if needed to answer user query or identify datasets if it is a data query
    """
    user_input = state['messages'][0].content if state['messages'] else ''
    tool_results = state.get("tool_results", [])

    try:
        if not user_input:
            error_data = {
                "error": "No user query provided",
                "is_data_query": False
            }
            return {
                "user_query": user_input,
                "query_type": "conversational",
                "messages": [ErrorMessage.from_text(json.dumps(error_data, indent=2))],
            }


        prompt = create_llm_prompt(user_input, tool_results)
        response: Any = lc.llm.invoke(prompt)
        parser = JsonOutputParser()

        if has_tool_calls(response):
            return {
                "user_query": user_input,
                "query_type": "tool_only",
                "messages": [response if isinstance(response, AIMessage) else AIMessage(content=str(response))],
            }

        response_content = str(response.content)
        parsed_content = parser.parse(response_content)

        return {
            "user_query": user_input,
            "query_type": parsed_content.get("query_type", "conversational"),
            "messages": [IntermediateStep.from_text(json.dumps(parsed_content, indent=2))],
        }

    except Exception as e:
        error_msg = f"Error identifying datasets: {str(e)}"
        return {
            "user_query": user_input,
            "query_type": "conversational",
            "messages": [ErrorMessage.from_text(json.dumps({"error": error_msg}, indent=2))]
        }

def route_from_analysis(state: State) -> str:
    """
    Route to the appropriate next node based on query analysis

    Args:
        state: Current state with analysis results

    Returns:
        String name of the next node to route to
    """

    last_message = state["messages"][-1]
    if has_tool_calls(last_message):
        return "tools"

    query_type = state.get("query_type", "conversational")

    if query_type == "conversational" or query_type == "tool_only":
        return "basic_conversation"
    else:
        return "identify_datasets"