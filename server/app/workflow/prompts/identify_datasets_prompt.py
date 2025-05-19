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
        You're a data analysis assistant. Identify relevant datasets for this
        query:
        "{user_query}"

        Pre-filtered datasets (by relevance):
        {json.dumps(available_datasets_schemas, indent=2)}

        INSTRUCTIONS:
        1. The datasets above have been pre-filtered using semantic search
           based on relevance to the user query.
        2. Based on the user query, confirm which of these pre-filtered
           datasets best matches the user's needs(select multiple if needed).
        3. For each selected dataset, identify:
           - The specific columns that will be needed for the analysis
           - For string columns: provide both exact and fuzzy values
           - Don't include the column names that are numeric type

        Task:
        1. Select the best matching dataset(s) from above
        2. For each selected dataset, identify:
           - Required columns for analysis
           - For string columns: provide exact and fuzzy values

        Response format:
        {{
            "selected_dataset": ["dataset_name1", "dataset_name2", ...],
            "reasoning": "Why these datasets were selected",
            "column_assumptions": [
                {{
                    "dataset": "dataset_name1",
                    "columns": [
                        {{
                            "name": "column_name",
                            "exact_values": ["value1", "value2", ...],
                            "fuzzy_values": ["partial1", "related1", ...]
                        }}
                    ]
                }}
            ]
        }}

        Guidelines:
        - exact_values: Confident matches for SQL equality
          (LOWER(column) = LOWER('value'))
        - fuzzy_values: Partial/approximate matches for LIKE queries
          (LOWER(column) LIKE LOWER('%value%'))
        - Use realistic values (e.g., "alice", "finance") not labels
        - Always reference datasets using the 'name' field
    """
