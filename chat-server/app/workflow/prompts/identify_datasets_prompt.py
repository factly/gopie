import json

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)


def create_identify_datasets_prompt(**kwargs) -> list | ChatPromptTemplate:
    prompt_template = kwargs.get("prompt_template", False)
    input_content = kwargs.get("input", "")

    system_content = """
TASK: Process dataset schemas and provide column assumptions for analysis.

INSTRUCTIONS:

There are TWO types of datasets provided:

1. REQUIRED DATASETS (Auto-Selected):
   * These datasets are ALREADY SELECTED and will be used automatically
   * You do NOT need to choose whether to include them
   * These will be part of your final analysis

2. SEMANTIC SEARCHED DATASETS (Need Selection):
   * Choose the dataset(s) that best match the user query based on usefulness and relevance
   * You can select multiple datasets if needed
   * Always refer to datasets by their "Table SQL Name"
   * IMPORTANT: The query type and confidence score were determined by a previous LLM step.
     Do NOT rely solely on the query type or confidence score - use your own reasoning to determine if datasets are useful
   * If datasets are relevant and useful for answering the query, select them REGARDLESS of query type or confidence score
   * Your primary goal is to select datasets that help answer the user's question effectively

COLUMN ASSUMPTIONS:
* Provide column assumptions for ALL datasets that will be used (required datasets + selected datasets from semantic search)
* List ONLY the columns needed for the query
* For string columns ONLY, provide:
    - "exact_values": actual values seen in sample_data that match the query terms
    - "fuzzy_values": search terms or substrings to help match the column values; provide meaningful text values that can be used to match the column values in that dataset, avoiding numeric or unprocessable values

VALUE GUIDELINES:
* Provide REAL values (e.g., "finance", "Alice") NOT placeholders
* Both exact_values and fuzzy_values refer to actual data values, not column names
* Include ONLY string columns in the values list
* DO NOT include numerical or nonsensical values in fuzzy_values that cannot be used to effectively match data
* Only use exact_values when completely confident the value exists in sample_data

NODE MESSAGE:
* Include a brief informative message to pass to subsequent nodes
* This message should describe what datasets were selected (from semantic search) and why
* Mention the required datasets that are automatically included
* If no additional datasets were selected from semantic search, explain why
* Be concise but informative - this will help guide later processing

FORMAT YOUR RESPONSE AS JSON:
{{
    "selected_dataset": ["dataset_name1", "dataset_name2", ...],  // Only from SEMANTIC SEARCHED datasets
    "reasoning": "1-2 sentences explaining why these datasets were selected from semantic search",
    "column_assumptions": [
        {{
            "dataset": "dataset_name1",  // Can be from REQUIRED or SELECTED datasets
            "columns": [
                {{
                    "name": "column_name",
                    "exact_values": ["value1", ...],
                    "fuzzy_values": ["value2", ...]
                }}
            ]
        }}
    ],
    "node_message": "Brief message about all datasets (required + selected) and their relevance to the query"
}}

IMPORTANT:
* selected_dataset should ONLY contain datasets chosen from semantic searched datasets
* column_assumptions should include ALL datasets (both required and selected)
* Always use the dataset "Table SQL Name" field (not "name" field)
* Only use exact_values when completely confident the value exists
* Make your node_message informative providing context on all datasets being used
"""

    human_template_str = """
{input}
"""

    if prompt_template:
        return ChatPromptTemplate.from_messages(
            [
                SystemMessagePromptTemplate.from_template(system_content),
                HumanMessagePromptTemplate.from_template(human_template_str),
            ]
        )

    human_content = human_template_str.format(input=input_content)

    return [
        SystemMessage(content=system_content),
        HumanMessage(content=human_content),
    ]


def format_identify_datasets_input(
    user_query: str,
    required_dataset_schemas: str = "[]",
    semantic_searched_datasets: str = "[]",
    confidence_score: float | None = None,
    query_type: str | None = None,
) -> dict:
    input_parts = [
        f"USER QUERY: {user_query}",
    ]

    if query_type:
        input_parts.append(f"QUERY TYPE: {query_type}")

    if confidence_score is not None:
        input_parts.append(f"CONFIDENCE SCORE: {confidence_score}/10")

    try:
        required_schemas = (
            json.loads(required_dataset_schemas)
            if isinstance(required_dataset_schemas, str)
            else required_dataset_schemas or []
        )

        semantic_schemas = (
            json.loads(semantic_searched_datasets)
            if isinstance(semantic_searched_datasets, str)
            else semantic_searched_datasets or []
        )

        if required_schemas:
            input_parts.append(
                f"\n=== REQUIRED DATASETS (Auto-Selected): {len(required_schemas)} ==="
            )
            input_parts.append(
                "These datasets are ALREADY SELECTED and will be used automatically."
            )
            input_parts.append(
                "Provide column assumptions for these datasets."
            )

            for i, schema in enumerate(required_schemas, 1):
                dataset_section = [f"\n--- REQUIRED DATASET {i} ---"]
                dataset_section.append(
                    f"Name: {schema.get('name', 'Unknown')}"
                )
                dataset_section.append(
                    f"Table Name (for SQL): {schema.get('dataset_name', schema.get('name', 'Unknown'))}"
                )

                if schema.get("dataset_description"):
                    dataset_section.append(
                        f"Description: {schema.get('dataset_description')}"
                    )

                columns = schema.get("columns", [])
                if columns:
                    dataset_section.append(f"Columns ({len(columns)}):")
                    dataset_section.extend(_format_columns(columns))

                input_parts.extend(dataset_section)
        else:
            input_parts.append("\n=== REQUIRED DATASETS: None ===")

        if semantic_schemas:
            input_parts.append(
                f"\n=== SEMANTIC SEARCHED DATASETS (Choose from these): {len(semantic_schemas)} ==="
            )
            input_parts.append(
                "SELECT the most relevant datasets from these options:"
            )

            for i, schema in enumerate(semantic_schemas, 1):
                dataset_section = [f"\n--- AVAILABLE DATASET {i} ---"]
                dataset_section.append(
                    f"Name: {schema.get('name', 'Unknown')}"
                )
                dataset_section.append(
                    f"Table Name (for SQL): {schema.get('dataset_name', schema.get('name', 'Unknown'))}"
                )

                if schema.get("dataset_description"):
                    dataset_section.append(
                        f"Description: {schema.get('dataset_description')}"
                    )

                columns = schema.get("columns", [])
                if columns:
                    dataset_section.append(f"Columns ({len(columns)}):")
                    dataset_section.extend(_format_columns(columns))

                input_parts.extend(dataset_section)
        else:
            input_parts.append(
                "\n=== SEMANTIC SEARCHED DATASETS: None available ==="
            )

        if not required_schemas and not semantic_schemas:
            input_parts.append("\nNo datasets available for analysis")

    except (json.JSONDecodeError, TypeError) as e:
        input_parts.append(f"\nError parsing dataset schemas: {str(e)}")
        input_parts.append(f"Required schemas: {required_dataset_schemas}")
        input_parts.append(f"Semantic schemas: {semantic_searched_datasets}")

    formatted_input = "\n".join(input_parts)

    return {
        "input": formatted_input,
    }


def _format_columns(columns: list) -> list:
    """Helper function to format column information consistently."""
    formatted_columns = []

    for column in columns:
        col_info = []
        col_name = column.get("column_name", "unknown")
        col_type = column.get("column_type", "unknown")
        col_info.append(f"- {col_name} ({col_type})")

        if column.get("column_description"):
            col_info.append(
                f"  Description: {column.get('column_description')}"
            )

        if col_type in [
            "BIGINT",
            "INTEGER",
            "DOUBLE",
            "FLOAT",
            "DECIMAL",
            "NUMERIC",
        ]:
            stats = []
            if column.get("min") is not None:
                stats.append(f"Range: {column.get('min')}-{column.get('max')}")
            if column.get("avg") is not None:
                stats.append(f"Avg: {column.get('avg')}")
            if column.get("count"):
                stats.append(f"Count: {column.get('count')}")
            if stats:
                col_info.append(f"  Stats: {', '.join(stats)}")

        sample_values = column.get("sample_values", [])
        if sample_values:
            unique_samples = list(dict.fromkeys(sample_values))[:5]
            samples_str = ", ".join(
                str(s) for s in unique_samples if s is not None
            )
            if samples_str:
                col_info.append(f"  Samples: {samples_str}")

        if column.get("approx_unique") is not None:
            col_info.append(f"  Unique values: ~{column.get('approx_unique')}")

        formatted_columns.extend(col_info)

    return formatted_columns
