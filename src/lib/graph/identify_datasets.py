from src.lib.graph.types import IntermediateStep, ErrorMessage, State
from langchain_core.messages import AIMessage
from typing import Dict, Any, List
import json
from src.lib.config.langchain_config import lc
from langchain_core.output_parsers import JsonOutputParser

def create_llm_prompt(user_query: str, ToolResult: List[Dict[str, Any]]) -> str:
    """Create a prompt for the LLM to identify the relevant dataset"""
    return f"""
        You are an AI assistant helping with data analysis. You have access to various tools that can help you gather information about available datasets.

        User Query: {user_query}

        Tool Results: {ToolResult}

        First, determine if this query is related to data analysis. If it is, you should use tools to:
        1. Discover what datasets are available
        2. Explore the datasets to understand their structure and content
        3. Determine which datasets are most relevant to the user's query and the information you have gathered from using tools

        You should NOT make assumptions about what datasets are available. Instead, use tools to gather this information.

        If the user is just greeting, chatting, or asking general questions or directly asking for information that just require tool calls and no working like generating and executing sql query and not related to data analysis, for that you don't need to use tools or select datasets.

        Respond in one of two ways:

        1. If this is a data-related query, use tool calls to gather information about available datasets.

        2. After you have gathered required information that is sufficient for the user query than Analyze the query and respond in JSON format:
        {{
            "selected_dataset": ["list of dataset names that are most relevant to the user query"],
            "reasoning": "brief explanation of why this dataset is relevant or why no dataset was selected",
            "is_data_query": true/false (whether this is a data-related query or just conversation)
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