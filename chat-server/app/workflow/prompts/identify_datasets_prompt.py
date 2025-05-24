import json
from typing import List

from app.models.schema import DatasetSchema


def create_identify_datasets_prompt(
    user_query: str, available_datasets_schemas: List[DatasetSchema]
) -> str:
    """
    Create a prompt for identifying datasets based on user query.

    Args:
        user_query: The natural language query from the user
        available_datasets_schemas: List of available dataset schemas

    Returns:
        A formatted prompt string
    """
    return f"""
        TASK: Identify the most relevant dataset(s) for this user query.

        USER QUERY: "{user_query}"

        AVAILABLE DATASETS (pre-filtered by relevance):
        {json.dumps(available_datasets_schemas, indent=2)}

        INSTRUCTIONS:

        1. SELECT DATASETS
        * Choose the dataset(s) that best match the user query
        * You can select multiple datasets if needed
        * Always refer to datasets by their "name" field

        2. IDENTIFY REQUIRED COLUMNS
        * For each selected dataset, list ONLY the columns needed for the query
        * For string columns ONLY, provide two types of search values:
            - "exact_values": Use when 100% confident value exists
            (Used in: WHERE LOWER(column) = LOWER('value'))
            - "fuzzy_values": Use when less confident about exact match
            (Used in: WHERE LOWER(column) LIKE LOWER('%value%'))

        3. VALUE GUIDELINES
        * Provide REAL VALUES (e.g., "finance", "Alice") NOT placeholders
        * Both exact/fuzzy values refer to actual data values, not column names
        * Include ONLY string columns in the values list
        * DO NOT include numerical columns used for mathematical calculations

        FORMAT YOUR RESPONSE AS JSON:
        {{
            "selected_dataset": ["dataset_name1", "dataset_name2", ...],
            "reasoning": "1-2 sentences explaining why these datasets were
                         selected",
            "column_assumptions": [
                {{
                    "dataset": "dataset_name1",
                    "columns": [
                        {{
                            "name": "column_name",
                            "exact_values": ["value1", ...],
                            "fuzzy_values": ["value2", ...]
                        }}
                    ]
                }}
            ]
        }}

        IMPORTANT:
        * Be specific and precise
        * Only select truly relevant datasets
        * Only include columns actually needed for the query
        * Always use the dataset "name" field (not ID)
        * Only use exact_values when completely confident the value exists
    """
