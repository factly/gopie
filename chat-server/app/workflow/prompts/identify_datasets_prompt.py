import json

from langchain_core.messages import HumanMessage, SystemMessage


def create_identify_datasets_prompt(
    input: str,
) -> list:
    system_content = """
TASK: Identify the most relevant dataset(s) for this user query.

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
{
    "selected_dataset": ["dataset_name1", "dataset_name2", ...],
    "reasoning": "1-2 sentences explaining why these datasets were selected",
    "column_assumptions": [
        {
            "dataset": "dataset_name1",
            "columns": [
                {
                    "name": "column_name",
                    "exact_values": ["value1", ...],
                    "fuzzy_values": ["value2", ...]
                }
            ]
        }
    ],
    "node_message": "Brief message about datasets found/not found and why
                     they're relevant to the query"
}

IMPORTANT:
* Be specific and precise
* Only select truly relevant datasets
* Only include columns actually needed for the query
* Always use the dataset "name" field (not ID)
* Only use exact_values when completely confident the value exists
* Make your node_message informative providing context on the datasets you selected
"""

    human_content = f"""
{input}
"""

    return [
        SystemMessage(content=system_content),
        HumanMessage(content=human_content),
    ]


def format_identify_datasets_input(
    user_query: str,
    available_datasets_schemas: str,
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
        schemas = (
            json.loads(available_datasets_schemas)
            if isinstance(available_datasets_schemas, str)
            else available_datasets_schemas
        )

        if schemas:
            input_parts.append(f"\nAVAILABLE DATASETS: {len(schemas)}")

            for i, schema in enumerate(schemas, 1):
                dataset_section = [f"\n--- DATASET {i} ---"]
                dataset_section.append(
                    f"Name: {schema.get('name', 'Unknown')}"
                )

                if schema.get("dataset_description"):
                    dataset_section.append(
                        f"Description: {schema.get('dataset_description')}"
                    )

                columns = schema.get("columns", [])
                if columns:
                    dataset_section.append(f"Columns ({len(columns)}):")

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
                                stats.append(
                                    f"Range: {column.get('min')}-{column.get('max')}"
                                )
                            if column.get("avg") is not None:
                                stats.append(f"Avg: {column.get('avg')}")
                            if column.get("count"):
                                stats.append(f"Count: {column.get('count')}")
                            if stats:
                                col_info.append(f"  Stats: {', '.join(stats)}")

                        sample_values = column.get("sample_values", [])
                        if sample_values:
                            unique_samples = list(
                                dict.fromkeys(sample_values)
                            )[:5]
                            samples_str = ", ".join(
                                str(s) for s in unique_samples if s is not None
                            )
                            if samples_str:
                                col_info.append(f"  Samples: {samples_str}")

                        if column.get("approx_unique") is not None:
                            col_info.append(
                                f"  Unique values: ~{column.get('approx_unique')}"
                            )

                        dataset_section.extend(col_info)

                input_parts.extend(dataset_section)
        else:
            input_parts.append("\nNo datasets available for analysis")

    except (json.JSONDecodeError, TypeError) as e:
        input_parts.append(f"\nError parsing dataset schemas: {str(e)}")
        input_parts.append(f"Raw schemas data: {available_datasets_schemas}")

    formatted_input = "\n".join(input_parts)

    return {
        "input": formatted_input,
    }
