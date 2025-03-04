import json
from langchain_core.output_parsers import JsonOutputParser
from typing import Dict, Any, List
from src.lib.graph.types import ErrorMessage, State, IntermediateStep
from src.lib.config.langchain_config import lc
from rich.console import Console
from src.utils.dataset_info import get_dataset_preview

console = Console()

def create_query_prompt(user_query: str, datasets_info: List[Dict[str, Any]], error_message: str = "", attempt: int = 1) -> str:
    """Create a prompt for the LLM to generate a SQL query"""
    error_context = ""
    if error_message and attempt > 1:
        error_context = f"""
        Previous attempt failed with this error:
        {error_message}

        Please fix the issues in the query and try again. This is attempt {attempt} of 3.
        """

    datasets_context = []
    for dataset_info in datasets_info:
        metadata = dataset_info.get("metadata", {})
        sample_data = dataset_info.get("sample_data", [])

        dataset_context = f"""
        Dataset: {metadata.get('name', '')}
        Total Rows: {metadata.get('total_rows', 0)}

        Columns:
        {json.dumps(metadata.get('columns', []), indent=2)}

        Column Types:
        {json.dumps(metadata.get('column_types', {}), indent=2)}

        Sample Values for Each Column:
        {json.dumps(metadata.get('sample_values', {}), indent=2)}

        Sample Rows:
        {json.dumps(sample_data, indent=2)}
        """
        datasets_context.append(dataset_context)

    all_datasets_context = "\n\n=== NEXT DATASET ===\n\n".join(datasets_context)

    return f"""
        Given the following natural language query and detailed information about multiple datasets, create an appropriate SQL query.

        User Query: "{user_query}"

        Available Datasets:
        {all_datasets_context}

        Error Context: {error_context}

        IMPORTANT GUIDELINES:
        1. Use the EXACT column names as shown in the dataset information
        2. Create a query that directly addresses the user's question
        3. If the user's query refers to a time period that doesn't match the dataset format (e.g., asking for 2018 when dataset uses 2018-19), adapt accordingly
        4. Make sure to handle column names correctly, matching the exact names in the dataset metadata
        5. Use the sample data as reference for the data format and values
        6. If the query requires joining multiple datasets, make sure to:
           - Use appropriate join conditions
           - Handle potentially conflicting column names
           - Specify table aliases if needed
           - Consider the relationship between datasets

        Respond in this JSON format:
        {{
            "sql_query": "the SQL query to fetch the required data",
            "explanation": "brief explanation of what the query does",
            "tables_used": ["list of tables needed"],
            "joins_required": [
                {{
                    "left_table": "name of left table",
                    "right_table": "name of right table",
                    "join_type": "type of join (INNER, LEFT, etc.)",
                    "join_conditions": ["list of join conditions"]
                }}
            ],
            "expected_result": "description of what the query will return"
        }}
    """

def plan_query(state: State) -> dict:
    """
    Plan the SQL query based on user input and dataset information.
    Makes a single attempt at query planning, handling various error conditions gracefully.
    Uses all selected datasets and their relationships.
    """
    try:
        selected_datasets = state.get("datasets", [])

        user_query = state.get("user_query", "")
        retry_count = state.get("retry_count", 0)

        # This error message might be from execute_query node or analyze_dataset node
        last_message = state.get("messages", [])[-1]
        last_error = str(last_message.content) if isinstance(last_message, ErrorMessage) else ""

        if not selected_datasets:
            error_msg = "No dataset selected for query planning"
            return {
                "messages": [ErrorMessage.from_text(json.dumps({"error": error_msg}, indent=2))]
            }

        datasets_info = []
        for dataset_name in selected_datasets:
            try:
                dataset_info = get_dataset_preview(dataset_name)
                datasets_info.append(dataset_info)
            except Exception as e:
                console.print(f"[yellow]Warning: Could not get preview for dataset {dataset_name}: {str(e)}[/yellow]")

        if not datasets_info:
            error_msg = "Could not get preview information for any of the selected datasets"
            return {
                "messages": [ErrorMessage.from_text(json.dumps({"error": error_msg}, indent=2))]
            }

        llm_prompt = create_query_prompt(user_query, datasets_info, last_error, retry_count + 1)

        response = lc.llm.invoke(llm_prompt)
        response_content = str(response.content)

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
