import json
from typing import Dict, List, Optional


def create_query_prompt(
    user_query: str,
    datasets_info: dict,
    error_message: Optional[List[Dict]] = None,
    attempt: int = 1,
) -> str:
    """
    Create a prompt for planning a SQL query based on user input and dataset
    information.

    Args:
        user_query: The natural language query from the user
        datasets_info: Information about the available datasets
        error_message: Any error messages from previous attempts
        attempt: The current attempt number

    Returns:
        A formatted prompt string
    """
    error_context = ""
    if error_message and attempt > 1:
        error_context = f"""
        Previous attempt failed with this error:
        {error_message}

        Please fix the issues in the query and try again. This is attempt
        {attempt} of 3.
        """
    return f"""
        Given the following natural language query and detailed information
        about multiple datasets, create an appropriate SQL query.

        User Query: "{user_query}"

        Selected Datasets Information:
        {json.dumps(datasets_info, indent=2)}

        IMPORTANT - DATASET NAMING:
        - Each dataset has a 'name' (user-friendly name) and an 'dataset_name'
          (the real table name in the database)
        - In your SQL query, you MUST use the dataset_name from the
          datasets_info
        - Example: If a dataset is shown as "COVID-19 Cases" to the user, its
          actual table name might be "ASD_ASDRDasdfaW"
        - Reference the provided `dataset_name_mapping` for the correct mapping

        IMPORTANT - CASE SENSITIVITY:
        - When comparing column values (not column names), use LOWER() function
          for case-insensitive matching
        - Example: WHERE LOWER(column_name) = LOWER('value')
        - Do NOT use LOWER() for column names or table/dataset names

        Error Context: {error_context}

        IMPORTANT GUIDELINES:
        1. Use the EXACT column names as shown in the dataset information
        2. Create a query that directly addresses the user's question
        3. If the user's query refers to a time period that doesn't match the
           dataset format (e.g., asking for 2018 when dataset uses 2018-19),
           adapt accordingly
        4. Make sure to handle column names correctly, matching the exact names
           in the dataset metadata
        5. Use the sample data as reference for the data format and values
        6. If the query requires joining multiple datasets, make sure to:
           - Use appropriate join conditions
           - Handle potentially conflicting column names
           - Specify table aliases if needed
           - Consider the relationship between datasets
        7. For text comparisons, use LOWER() function on both sides to ensure
           case-insensitive matching

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
