import json
from typing import List

from app.models.schema import DatasetSchema


def create_identify_datasets_prompt(
    user_query: str,
    available_datasets_schemas: List[DatasetSchema],
    confidence_score: float | None = None,
    query_type: str | None = None,
) -> str:
    """
    Create a prompt for identifying datasets based on user query.

    Args:
        user_query: The natural language query from the user
        available_datasets_schemas: List of available dataset schemas
        confidence_score: Confidence score for the query classification
        query_type: Type of query determined by previous analysis

    Returns:
        A formatted prompt string
    """
    query_info = ""
    if query_type is not None:
        query_info = f"\nQUERY TYPE: {query_type}"

    if confidence_score is not None:
        query_info += f"\nQUERY CONFIDENCE SCORE: {confidence_score}"

    return f"""
        TASK: Identify the most relevant dataset(s) for this user query.

        USER QUERY: "{user_query}"{query_info}

        AVAILABLE DATASETS (pre-filtered by relevance):
        {json.dumps(available_datasets_schemas, indent=2)}

        INSTRUCTIONS:

        1. SELECT DATASETS
        * Choose the dataset(s) that best match the user query based on
          usefulness and relevance
        * You can select multiple datasets if needed
        * Always refer to datasets by their "name" field
        * IMPORTANT: The query type and confidence score were determined
          by a previous LLM step. Do NOT rely solely on the query type
          or confidence score - use your own reasoning to determine if
          datasets are useful
        * If datasets are relevant and useful for answering the query,
          select them REGARDLESS of query type or confidence score
        * Your primary goal is to select datasets that help answer the
          user's question effectively

        2. IDENTIFY REQUIRED COLUMNS
        * For each selected dataset, list ONLY the columns needed for the query
        * For string columns ONLY, provide two types of search values:
            - "exact_values": Use ONLY when the EXACT value appears in the
              sample_data of the schema. If you cannot see the exact value
              in the sample_data, DO NOT use exact_values.
            (Used in: WHERE LOWER(column) = LOWER('value'))
            - "fuzzy_values": Use when the exact value is NOT in sample_data
              or when less confident about exact match
            (Used in: WHERE LOWER(column) LIKE LOWER('%value%'))

        3. VALUE GUIDELINES
        * Provide REAL VALUES (e.g., "finance", "Alice") NOT placeholders
        * Both exact/fuzzy values refer to actual data values, not column names
        * Include ONLY string columns in the values list
        * DO NOT include numerical columns used for mathematical calculations

        4. PROVIDE NODE MESSAGE
        * Include a brief informative message to pass to subsequent nodes
        * This message should describe what datasets were found and why
        * If no datasets were found, explain why and what alternative approach
          might work
        * Be concise but informative - this will help guide later processing

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
            ],
            "node_message": "Brief message about datasets found/not found and
                           why they're relevant to the query"
        }}

        IMPORTANT:
        * Be specific and precise
        * Only select truly relevant datasets
        * Only include columns actually needed for the query
        * Always use the dataset "name" field (not ID)
        * Only use exact_values when completely confident the value exists
        * Make your node_message informative for subsequent processing steps
    """
