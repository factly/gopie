import json
from langchain_core.output_parsers import JsonOutputParser
from typing import Dict, Any, Union, List
from lib.graph.types import ErrorMessage, State, IntermediateStep
from lib.langchain_config import lc
from rich.console import Console

console = Console()

def create_query_prompt(user_query: str, datasets_metadata: Union[Dict[str, Any], List, Any], error_message: str = "", attempt: int = 1) -> str:
    """Create a prompt for the LLM to generate a SQL query"""
    error_context = ""
    if error_message and attempt > 1:
        error_context = f"""
        Previous attempt failed with this error:
        {error_message}

        Please fix the issues in the query and try again. This is attempt {attempt} of 3.
        """

    return f"""
        Given the following natural language query and dataset information, create an appropriate SQL query.

        User Query: "{user_query}"

        Available Dataset Information:
        {json.dumps(datasets_metadata, indent=2)}
        {error_context}

        IMPORTANT GUIDELINES:
        1. Use the EXACT dataset name provided in the metadata (without file extensions)
        2. Create a query that directly addresses the user's question
        3. If the user's query refers to a time period that doesn't match the dataset format (e.g., asking for 2018 when dataset uses 2018-19), adapt accordingly
        4. Make sure to handle column names correctly, matching the exact names in the dataset metadata

        Respond in this JSON format:
        {{
            "sql_query": "the SQL query to fetch the required data",
            "explanation": "brief explanation of what the query does",
            "tables_used": ["list of tables needed"],
            "joins_required": [],
            "expected_result": "description of what the query will return"
        }}
    """

def plan_query(state: State) -> dict:
    """
    Plan the SQL query based on user input and dataset information.
    Makes a single attempt at query planning, handling various error conditions gracefully.
    Uses the selected dataset if available, otherwise uses all datasets.
    """
    try:
        datasets_metadata = state.get("datasets", {})
        user_query = state.get("user_query", "")
        retry_count = state.get("retry_count", 0)

        # Get the selected dataset from the previous step
        selected_dataset = None
        if state.get("messages", []):
            try:
                # Try to parse the last step's output to get the selected dataset
                last_step_message = state.get("messages", [])[-1]
                if hasattr(last_step_message, 'content'):
                    parser = JsonOutputParser()
                    parsed_content = parser.parse(last_step_message.content)
                    selected_dataset = parsed_content.get("selected_dataset", "")
            except Exception:
                # If parsing fails, we'll use all datasets
                pass

        # Filter the datasets to only include the selected one if available
        if selected_dataset and selected_dataset in datasets_metadata:
            filtered_datasets = {selected_dataset: datasets_metadata[selected_dataset]}
        else:
            filtered_datasets = datasets_metadata

        last_message = state.get("messages", [])[-1]
        last_error = str(last_message.content) if isinstance(last_message, ErrorMessage) else ""

        llm_prompt = create_query_prompt(user_query, filtered_datasets, last_error, retry_count + 1)

        response = lc.llm.invoke(llm_prompt)
        response_content = str(response.content) if hasattr(response, 'content') else str(response)

        parser = JsonOutputParser()
        try:
            parsed_response = parser.parse(response_content)

            required_fields = ["sql_query", "explanation", "tables_used", "expected_result"]
            missing_fields = [field for field in required_fields if field not in parsed_response]

            if missing_fields:
                error_msg = f"Missing required fields in LLM response: {', '.join(missing_fields)}"
                return {
                    "messages": [ErrorMessage.from_text(json.dumps({"error": error_msg}, indent=2))]
                }

            sql_query = parsed_response.get("sql_query", "")

            if not sql_query:
                error_msg = "LLM returned empty SQL query"
                return {
                    "messages": [ErrorMessage.from_text(json.dumps({"error": error_msg}, indent=2))]
                }

            return {
                "query": sql_query,
                "messages": [IntermediateStep.from_text(json.dumps(parsed_response, indent=2))]
            }

        except Exception as parse_error:
            error_msg = f"Failed to parse LLM response: {str(parse_error)}"
            return {
                "messages": [ErrorMessage.from_text(json.dumps({"error": error_msg}, indent=2))]
            }

    except Exception as e:
        error_msg = f"Unexpected error in query planning: {str(e)}"
        return {
            "messages": [ErrorMessage.from_text(json.dumps({"error": error_msg}, indent=2))]
        }
