import json
from langchain_core.output_parsers import JsonOutputParser
from typing import Optional, Dict, Any, List, Union
from lib.graph.types import ErrorMessage, State, IntermediateStep
from lib.langchain_config import lc
from rich.console import Console

console = Console()

def format_sample_data_section(sample_data: Optional[Dict[str, Any]] = None) -> str:
    """Format sample data into readable text section.

    Args:
        sample_data: Dictionary mapping dataset names to sample rows of data

    Returns:
        Formatted string with sample data or empty string if none
    """
    if not sample_data:
        return ""

    sample_data_text = []
    for dataset_name, rows in sample_data.items():
        sample_data_text.append(f"Sample data for {dataset_name}:")
        sample_data_text.append(json.dumps(rows, indent=2))

    return "\n\nSample Data:\n" + "\n\n".join(sample_data_text)

def query_prompt(user_query: str, datasets_metadata: list, sample_data: Optional[Dict[str, Any]] = None) -> str:
    """Create a prompt for the LLM to generate SQL query based on metadata and user query.

    Args:
        user_query: The user's natural language query
        datasets_metadata: List of dataset metadata
        sample_data: Dictionary mapping dataset names to sample rows of data

    Returns:
        Formatted prompt string for the LLM
    """
    sample_data_section = format_sample_data_section(sample_data)

    return f"""
        Given the following natural language query and dataset metadata, help me plan a SQL query.
        Your task is to understand the user's intent and create an appropriate SQL query plan.
        Dont modify the dataset name. use the exact dataset name provided in the metadata.
        Dont use the extension of the dataset name. for example if the dataset name is "sales.csv" dont use "sales.csv" instead use "sales.csv" only for generating the sql query.
        Improve the user prompt as needed, (e.g., the user asked for amount spent in year 2018, but the dataset year in range format like 2018-19 something like this, you can modify the user prompt to match the dataset format)

        User Query: "{user_query}"

        Available Dataset Information:
        {json.dumps(datasets_metadata, indent=2)}{sample_data_section}

        Please analyze the request and provide a detailed plan in JSON format:
        {{
            "sql_query": "the SQL query to fetch the required data",
            "explanation": "step-by-step explanation of the query logic",
            "tables_used": ["list of tables needed for this query"],
            "joins_required": ["any necessary table joins"],
            "expected_result": "description of the output format and data"
        }}

        Make sure to optimize the query and consider any necessary table relationships.
    """

def error_handling_prompt(previous_query: str, error: str, metadata=None, sample_data: Optional[Dict[str, Any]] = None) -> str:
    """Create a prompt for handling query errors.

    Args:
        previous_query: The SQL query that failed
        error: The error message
        metadata: Dataset metadata
        sample_data: Dictionary mapping dataset names to sample rows of data

    Returns:
        Formatted prompt string for error handling
    """
    metadata_section = f"\nAvailable Dataset Information:\n{json.dumps(metadata, indent=2)}" if metadata else ""
    sample_data_section = format_sample_data_section(sample_data)

    return f"""
        The following SQL query failed:
        {previous_query}

        With this error:
        {error}
        {metadata_section}{sample_data_section}

        Analyze the error and determine if the query can be fixed. If it can be fixed, provide a corrected query plan.
        If it cannot be fixed, explain why and indicate that we cannot proceed further.

        Respond in this JSON format:
        {{
            "can_fix": true/false,
            "explanation": "explanation of the error and fix/why it cannot be fixed",
            "sql_query": "corrected SQL query if can_fix is true",
            "tables_used": ["list of tables needed"],
            "joins_required": ["any necessary joins"],
            "expected_result": "description of expected output"
        }}

        If can_fix is false, include "cannot_plan_further" instead of the query details.
    """

def extract_error_content(message: Union[ErrorMessage, IntermediateStep, str]) -> str:
    """Extract error content from different message formats.

    Args:
        message: The message containing error information

    Returns:
        Extracted error content as string
    """
    if isinstance(message, str):
        return message
    elif hasattr(message, 'content'):
        content = message.content
        if isinstance(content, str):
            try:
                parsed = json.loads(content)
                if isinstance(parsed, dict) and "result" in parsed and "error" in parsed.get("result", "").lower():
                    return parsed.get("result", "")
                return content
            except json.JSONDecodeError:
                return content
        if isinstance(content, list) or not isinstance(content, str):
            return json.dumps(content)
        return content
    return str(message)

def create_cannot_plan_message(reason: str, original_error: str = "") -> Dict[str, Any]:
    """Create a standardized cannot-plan message.

    Args:
        reason: The reason planning cannot continue
        original_error: Optional original error message

    Returns:
        Dictionary with cannot plan information
    """
    message = {
        "cannot_plan_further": True,
        "reason": reason
    }

    if original_error:
        message["original_error"] = original_error

    return message

def plan_query(state: State) -> dict:
    """Plan the SQL query to be executed based on user input and dataset information.

    Args:
        state: The current state containing user query, dataset info, and message history

    Returns:
        Dictionary with query plan or error information
    """
    try:
        metadata = state.get("datasets", {})
        user_query = state.get("user_query", "")
        previous_query = state.get("query", "")
        sample_data = state.get("sample_data", {})
        error_detected = False
        error_message = ""

        # Check for error in previous messages
        if state['messages']:
            for message in reversed(state['messages']):
                if isinstance(message, ErrorMessage):
                    error_detected = True
                    error_message = extract_error_content(message)
                    break
                elif isinstance(message, IntermediateStep):
                    try:
                        # Ensure content is a string before parsing
                        if isinstance(message.content, str):
                            content = json.loads(message.content)
                            if "result" in content and "error" in content.get("result", "").lower():
                                error_detected = True
                                error_message = content.get("result", "")
                                break
                    except (json.JSONDecodeError, AttributeError):
                        pass

        if error_detected:
            llm_prompt = error_handling_prompt(previous_query, error_message, metadata, sample_data)
        else:
            llm_prompt = query_prompt(user_query, metadata, sample_data)

        response = lc.llm.invoke(llm_prompt)
        response_content = str(response.content) if hasattr(response, 'content') else str(response)

        try:
            parsed_response = json.loads(response_content)

            if error_detected and not parsed_response.get("can_fix", False):
                cannot_plan_message = create_cannot_plan_message(
                    parsed_response.get('explanation', 'Unable to correct query errors'),
                    error_message
                )
                return {
                    "cannot_plan_further": True,
                    "messages": [IntermediateStep.from_text(json.dumps(cannot_plan_message))]
                }

            return {
                "query": parsed_response["sql_query"],
                "messages": [IntermediateStep.from_text(json.dumps(parsed_response))]
            }

        except json.JSONDecodeError as je:
            reason = f"Error parsing {'error analysis' if error_detected else 'planning'} response: {str(je)}"
            cannot_plan_message = create_cannot_plan_message(reason, error_message if error_detected else "")
            return {
                "cannot_plan_further": True,
                "messages": [IntermediateStep.from_text(json.dumps(cannot_plan_message))]
            }

    except Exception as e:
        cannot_plan_message = create_cannot_plan_message(f"Error in query planning: {str(e)}")
        return {
            "cannot_plan_further": True,
            "messages": [IntermediateStep.from_text(json.dumps(cannot_plan_message))]
        }