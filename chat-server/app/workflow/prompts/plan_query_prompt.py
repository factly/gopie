from langchain_core.messages import HumanMessage, SystemMessage


def create_plan_query_prompt(input: str) -> list:
    system_content = """
# QUERY TASK
Given the following natural language query and detailed information
about multiple datasets, create appropriate SQL query or queries.

# DATABASE COMPATIBILITY REQUIREMENTS
IMPORTANT:
- Generated SQL queries MUST be compatible with DuckDB SQL execution
  engine.
- Avoid PostgreSQL-specific syntax and functions.

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

# DATASET RELATIONSHIP ASSESSMENT
1. ANALYZE whether the selected datasets can be related through common
   fields
   - Look for matching column names, primary/foreign keys, or semantic relationships
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
8. Never use ILIKE, LIKE operator while generating SQL query

# SQL FORMATTING REQUIREMENTS
You must provide a well-formatted version of the SQL query for UI display with:
   - SQL keywords in UPPERCASE
   - Each major clause on a new line
   - Proper indentation for readability
   - Consistent spacing around operators

# RESPONSE FORMAT
Respond in this JSON format:
{
    "reasoning": "Explain your overall thought process for planning the query. Discuss whether datasets can be joined.",
    "sql_queries": [
        {
            "sql_query": "the SQL query to fetch the required data",
            "explanation": "brief explanation of the overall query strategy",
            "tables_used": ["list of tables needed"],
            "expected_result": "description of what the query will return"
        }
    ],
    "limitations": "Any limitations or assumptions made when planning the query"
}

Note: If datasets are related and you only need one query,
"sql_queries" should contain only one element. If datasets aren't
related, include multiple queries in the "sql_queries" array, one for
each dataset needed.
"""

    human_content = f"""
{input}
"""

    return [
        SystemMessage(content=system_content),
        HumanMessage(content=human_content),
    ]


def format_plan_query_input(
    user_query: str,
    datasets_info: dict,
    error_messages: list | None = None,
    retry_count: int = 0,
    node_messages: dict | None = None,
) -> dict:
    input_parts = [
        f"USER QUERY: {user_query}",
    ]

    if retry_count > 0:
        input_parts.append(f"RETRY ATTEMPT: {retry_count}/3")

    if datasets_info:
        input_parts.append("\n--- DATASETS INFORMATION ---")

        dataset_name_mapping = datasets_info.get("dataset_name_mapping", {})
        if dataset_name_mapping:
            input_parts.append("Dataset Name Mapping:")
            for user_name, db_name in dataset_name_mapping.items():
                input_parts.append(f"- '{user_name}' → table: {db_name}")

        schemas = datasets_info.get("schemas", [])
        if schemas:
            input_parts.append(f"\nDataset Schemas ({len(schemas)}):")

            for i, schema in enumerate(schemas, 1):
                schema_section = [
                    f"\n--- DATASET {i}: {schema.get('name', 'Unknown')} ---"
                ]
                schema_section.append(
                    f"Table Name: {schema.get('dataset_name', 'N/A')}"
                )

                if schema.get("dataset_description"):
                    schema_section.append(
                        f"Description: {schema.get('dataset_description')}"
                    )

                columns = schema.get("columns", [])
                if columns:
                    schema_section.append(f"Columns ({len(columns)}):")

                    for column in columns:
                        col_name = column.get("column_name", "unknown")
                        col_type = column.get("column_type", "unknown")
                        col_line = f"- {col_name} ({col_type})"

                        if column.get("column_description"):
                            col_line += (
                                f" - {column.get('column_description')}"
                            )

                        if col_type in [
                            "BIGINT",
                            "INTEGER",
                            "DOUBLE",
                            "FLOAT",
                            "DECIMAL",
                            "NUMERIC",
                        ]:
                            stats_info = []
                            if (
                                column.get("min") is not None
                                and column.get("max") is not None
                            ):
                                stats_info.append(
                                    f"Range: {column.get('min')}-{column.get('max')}"
                                )
                            if column.get("avg") is not None:
                                stats_info.append(f"Avg: {column.get('avg')}")
                            if stats_info:
                                col_line += f" [{', '.join(stats_info)}]"

                        sample_values = column.get("sample_values", [])
                        if sample_values:
                            unique_samples = list(
                                dict.fromkeys(sample_values)
                            )[:3]
                            samples_str = ", ".join(
                                str(s) for s in unique_samples if s is not None
                            )
                            if samples_str:
                                col_line += f" (samples: {samples_str})"

                        schema_section.append(col_line)

                input_parts.extend(schema_section)

        column_requirements = datasets_info.get(
            "correct_column_requirements", {}
        )
        if column_requirements:
            input_parts.append("\n--- COLUMN VALUE ANALYSIS ---")
            input_parts.append(
                "Verified column values from database analysis:"
            )

            datasets_analysis = column_requirements.get("datasets", {})
            for dataset_name, analysis in datasets_analysis.items():
                input_parts.append(f"\nDataset: {dataset_name}")
                columns_analyzed = analysis.get("columns_analyzed", [])

                for col_analysis in columns_analyzed:
                    col_name = col_analysis.get("column_name", "unknown")
                    input_parts.append(f"- Column: {col_name}")

                    verified_values = col_analysis.get("verified_values", [])
                    if verified_values:
                        exact_vals = [
                            v.get("value")
                            for v in verified_values
                            if v.get("found_in_database")
                        ]
                        if exact_vals:
                            input_parts.append(
                                f"  ✓ Exact matches found: {', '.join(exact_vals)}"
                            )

                    suggested_alternatives = col_analysis.get(
                        "suggested_alternatives", []
                    )
                    if suggested_alternatives:
                        for alt in suggested_alternatives:
                            if alt.get("found_similar_values"):
                                similar_vals = alt.get("similar_values", [])[
                                    :3
                                ]  # Limit to 3
                                if similar_vals:
                                    input_parts.append(
                                        f"  ⚠ Similar values for '{alt.get('requested_value')}': {', '.join(similar_vals)}"
                                    )

    if error_messages and retry_count > 0:
        input_parts.append("\n--- PREVIOUS ERRORS ---")
        input_parts.append(
            f"Previous attempt {retry_count} failed. Errors encountered:"
        )
        for error in error_messages:
            for error_type, error_msg in error.items():
                input_parts.append(f"- {error_type}: {error_msg}")
        input_parts.append(
            "Please analyze these errors and generate corrected SQL queries."
        )

    if node_messages:
        input_parts.append("\n--- WORKFLOW CONTEXT ---")
        input_parts.append("Previous workflow steps information:")
        for node, message in node_messages.items():
            if isinstance(message, dict):
                input_parts.append(f"- {node}:")
                for key, value in message.items():
                    input_parts.append(f"  {key}: {value}")
            else:
                input_parts.append(f"- {node}: {message}")

    formatted_input = "\n".join(input_parts)

    return {
        "input": formatted_input,
    }
