from src.lib.graph.types import IntermediateStep, ErrorMessage, State
from langchain_core.messages import AIMessage
from typing import Dict, Any, List
import json
from src.lib.config.langchain_config import lc
from langchain_core.output_parsers import JsonOutputParser

def create_llm_prompt(user_query: str, tool_results: List[Dict[str, Any]]) -> str:
    """Create a prompt for the LLM to identify the relevant dataset"""
    return f"""
        You are an AI assistant specialized in data analysis. Your role is to help users analyze data by identifying relevant datasets and tools.

        USER QUERY:
        "{user_query}"

        TOOL RESULTS:
        {tool_results}

        INSTRUCTIONS:
        1. First, determine if this is a data analysis query or a conversational query.

        2. For data analysis queries:
           - Use tools to discover available datasets
           - Explore dataset structures and content
           - Determine which datasets best match the user's needs
           - Do NOT assume what datasets are available - use tools to verify

        3. For conversational queries:
           - If the query is a general question, greeting, or casual conversation, handle it without tools
           - No dataset selection is needed for conversational queries

        4. For tool-only queries:
           - If the query can be answered directly with tool calls without dataset analysis, make those tool calls
           - Mark these as non-data queries in your response

        RESPONSE FORMAT:
        After gathering sufficient information, respond in this JSON format:
        {{
            "selected_dataset": ["dataset_name1", "dataset_name2"], // List of relevant datasets (empty if none)
            "reasoning": "Clear explanation of why these datasets were selected or why no datasets are relevant",
            "is_data_query": true/false // Whether this requires data analysis (true) or is conversational (false)
        }}
        """

def has_tool_calls(message):
    """Helper function to check if a message has tool calls"""
    if hasattr(message, 'tool_calls') and message.tool_calls:
        return True

    if hasattr(message, 'additional_kwargs') and 'tool_calls' in message.additional_kwargs:
        return True

    return False

def identify_datasets(state: State):
    """
    Use LLM to identify relevant dataset based on natural language query.
    This function can also generate tool calls if needed.
    """
    parser = JsonOutputParser()
    user_input = state['messages'][0].content if state['messages'] else ''
    ToolResult = state.get('tool_results', [])

    print("Result: ",ToolResult)

    try:
        if not user_input:
            error_data = {
                "error": "No user query provided",
                "is_data_query": False
            }
            return {
                "datasets": None,
                "user_query": user_input,
                "conversational": False,
                "messages": [ErrorMessage.from_text(json.dumps(error_data, indent=2))],
            }


        prompt = create_llm_prompt(user_input, ToolResult)
        response: Any = lc.llm.invoke(prompt)

        if has_tool_calls(response):
            return {
                "user_query": user_input,
                "conversational": False,
                "messages": [response if isinstance(response, AIMessage) else AIMessage(content=str(response))],
                "current_node": "identify_datasets"
            }

        response_content = str(response.content)
        parsed_content = parser.parse(response_content)

        return {
            "datasets": parsed_content.get("selected_dataset", []),
            "user_query": user_input,
            "conversational": not parsed_content.get("is_data_query", False),
            "messages": [IntermediateStep.from_text(json.dumps(parsed_content, indent=2))],
        }

    except Exception as e:
        error_msg = f"Error identifying datasets: {str(e)}"
        return {
            "datasets": None,
            "user_query": user_input,
            "conversational": False,
            "messages": [ErrorMessage.from_text(json.dumps({"error": error_msg}, indent=2))]
        }

def is_conversational_input(state: State) -> str:
    """
    If no dataset was selected, generate a response.
    If a dataset was selected, plan the query execution.
    If tool calls were generated, route to tools.
    """

    last_message = state["messages"][-1]
    if has_tool_calls(last_message):
        return "tools"

    parser = JsonOutputParser()

    try:
        response_content = last_message.content
        parsed_response = parser.parse(response_content)

        is_data_query = parsed_response.get("is_data_query", False)
        has_dataset = "selected_dataset" in parsed_response and parsed_response["selected_dataset"]

        if is_data_query and has_dataset:
            return "analyze_dataset"
        else:
            return "basic_conversation"
    except Exception as e:
        error_data = {
            "error": f"Error determining input type: {str(e)}",
            "is_data_query": False,
            "selected_dataset": "",
            "reasoning": "Failed to parse the previous response"
        }

        state["messages"][-1] = ErrorMessage.from_text(json.dumps(error_data, indent=2))
        return "basic_conversation"