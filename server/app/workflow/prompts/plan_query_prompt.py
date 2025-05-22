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

    formatted_datasets = json.dumps(datasets_info, indent=2)

    prompt = f"""
        # QUERY TASK
        Given the following natural language query and detailed information
        about multiple datasets, create appropriate SQL query or queries.

        User Query: "{user_query}"

        # DATASETS INFORMATION
        Selected Datasets Information:
        {formatted_datasets}

        # DATASET NAMING GUIDELINES
        IMPORTANT - DATASET NAMING:
        - Each dataset has a 'name' (user-friendly name) and an 'dataset_name'
          (the real table name in the database)
        - In your SQL query, you MUST use the dataset_name from the
          datasets_info
        - Example: If a dataset is shown as "COVID-19 Cases" to the user, its
          actual table name might be "ASD_ASDRDasdfaW"
        - Reference the provided `dataset_name_mapping` for the correct mapping

        # CASE SENSITIVITY GUIDELINES
        - When comparing column values (not column names), use LOWER() function
          for case-insensitive matching
        - Example: WHERE LOWER(column_name) = LOWER('value')
        - Do NOT use LOWER() for column names or table/dataset names

        # ERROR INFORMATION
        {error_context}

        # DATASET RELATIONSHIP ASSESSMENT
        1. ANALYZE whether the selected datasets can be related through common
           fields
           - Look for matching column names, primary/foreign keys, or semantic
             relationships
           - Determine if JOIN operations are possible between datasets

        2. DECISION POINT:
           a) If datasets ARE RELATED:
              - Create a SINGLE SQL query using appropriate JOINs
              - Use the most efficient join type (INNER, LEFT, etc.)

           b) If datasets are NOT RELATED (no sensible join possible):
              - Create MULTIPLE independent SQL queries (one per dataset)
              - Each query should extract the relevant information from its
                dataset

        # QUERY DEVELOPMENT GUIDELINES (IMPORTANT)
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
        8. Never use LIKE operator while generating SQL query

        # SQL FORMATTING REQUIREMENTS
        SQL FORMATTING REQUIREMENTS:
        You must provide two versions of the SQL query (or queries):
        1. "sql_query": A simple version for execution
        2. "formatted_sql_query": A well-formatted version for UI display with:
           - SQL keywords in UPPERCASE
           - Each major clause on a new line
           - Proper indentation for readability
           - Consistent spacing around operators

        # RESPONSE FORMAT
        Respond in this JSON format:
        {{
            "sql_queries": [
                {{
                    "sql_query": "the SQL query to fetch the required data",
                    "formatted_sql_query": "the well-formatted SQL query for
                                           UI display",
                    "explanation": "brief explanation of the overall query
                                    strategy",
                    "tables_used": ["list of tables needed"],
                    "expected_result": "description of what the query will
                                        return"
                }}
            ],
        }}

        Note: If datasets are related and you only need one query,
        "sql_queries" should contain only one element. If datasets aren't
        related, include multiple queries in the "sql_queries" array, one for
        each dataset needed.
    """

    return prompt
