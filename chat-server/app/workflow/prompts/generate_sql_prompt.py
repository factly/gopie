from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
)

from app.utils.prompts import escape_value
from app.workflow.graph.multi_dataset_graph.types import DatasetsInfo
from app.workflow.graph.single_dataset_graph.types import SingleDatasetInfo
from app.workflow.prompts.formatters.format_prompt_for_langsmith import (
    langsmith_compatible,
)


def generate_sql_prompt(**kwargs) -> list[BaseMessage] | ChatPromptTemplate:
    prompt_template = kwargs.get("prompt_template", False)
    input_content = kwargs.get("input", "")

    system_content = """
You are a DuckDB and data expert. Analyze the user's question and available datasets to determine if valid SQL queries can be generated.

## OUTPUT FORMAT RULES (CRITICAL — FOLLOW EXACTLY)

You must choose ONE path. The fields you fill depend on which path you choose.

**Path A — You ARE generating SQL** (datasets can answer the question):
- `sql_queries`: Put your SQL query or queries here. Each item needs: sql_query, explanation, tables_used.
- `non_sql_response`: MUST be empty string "".
- `user_friendly_response`: MUST be empty string "".
- `limitations`: REQUIRED. One or two short sentences: assumptions (e.g., join keys, same-ID across tables), missing data, units, or exclusions.

**Path B — You are NOT generating SQL** (data is insufficient, or answer is from context/sample only):
- `sql_queries`: MUST be empty list [].
- `non_sql_response`: REQUIRED. Clear, technical explanation of why no SQL (missing columns, incompatible data, answer from context, etc.).
- `user_friendly_response`: REQUIRED. Short (under 200 chars), non-technical message for the user (e.g., "I couldn't find the right data to run a query").
- `limitations`: REQUIRED. Brief note on what is missing or why SQL was not used.

Rule: If `sql_queries` has any items, then `non_sql_response` and `user_friendly_response` must both be "". Do NOT put intro text like "Here are the results" in `non_sql_response` when you generate SQL.

## SQL MODIFICATION REQUESTS
If the user query starts with [SQL_MODIFICATION: <type>], modify the PREVIOUS SQL QUERY/QUERIES to fulfill the user's request.
- Use the previous query/queries as the base structure
- Apply ONLY the change the user requested to each query
- Keep all other parts of each query intact (table names, existing columns, joins, etc.)
- The <type> indicates the kind of change needed (e.g., adding columns, filtering, sorting, etc.)
- If multiple queries are provided, apply modification accordingly to the relevant ones

## DECISION FRAMEWORK

### Step 1: Internal Validation (Do Not Expose)
Before responding, decide:
1. Can the dataset(s) answer the user's question?
2. Are the required columns in the schema(s)?
3. If multiple datasets, can they be joined correctly?
4. Can the question be answered from sample data or previous results alone?

### Step 2: Choose ONE Path
- **Path A**: Datasets can fulfill the query → generate SQL. Use Path A output rules above.
- **Path B**: Data insufficient, or answer from context/sample only → no SQL. Use Path B output rules above.

## DATABASE & QUERY RULES

### DuckDB Compatibility
- SQL must be valid DuckDB. Use exact table names from schema (dataset_name). No semicolon at end.
- Double quotes for identifiers; single quotes for string values. Only SELECT (read-only).

### Column & Table Usage
- Use EXACT column names from the schema (case-sensitive). Use the TABLE NAME from the schema.
- Include unit columns when showing value columns. Do NOT use project_id, dataset_id, or internal IDs in WHERE.

### Text Matching & Filtering
- Case-insensitive: `LOWER(column) = LOWER('value')`. No ILIKE or LIKE. Regex: `REGEXP_MATCHES(column, 'pattern')`.

### Calculations & Aggregations
- Share/percentage: `(value/total)*100`. Use summarize only for explicit summary requests.

### Multiple Datasets
- Related datasets: one query with JOINs. Unrelated: multiple separate queries.

## CONTEXT HANDLING

- Validation results: fix previous queries using the issues mentioned.
- Previous results: use as context; avoid re-running if they already answer the question.
- Error messages (retries): fix the mistakes and try again.

## SPECIAL INSTRUCTIONS
- Ignore visualization in the user query.
- Always set `limitations` (1–2 sentences on assumptions, missing data, or exclusions).
- In `sql_queries`, each `explanation` must be concise and technical.
- Focus on business data columns, not technical metadata.
"""

    human_template_str = "{input}"

    if prompt_template:
        return ChatPromptTemplate.from_messages(
            [
                SystemMessage(content=langsmith_compatible(system_content)),
                HumanMessagePromptTemplate.from_template(human_template_str),
            ]
        )

    human_content = human_template_str.format(input=input_content)

    return [
        SystemMessage(content=system_content),
        HumanMessage(content=human_content),
    ]


def format_generate_sql_input(
    user_query: str,
    datasets_info: DatasetsInfo | SingleDatasetInfo | None = None,
    retry_count: int = 0,
    prev_sql_queries: list | None = None,
    validation_result: str | None = None,
    dataset_info: str | None = None,
    error_messages: list | None = None,
    duckdb_docs_context: str | None = None,
    **kwargs,
) -> dict:
    input_str = f"USER QUERY: {user_query}\n"

    if retry_count > 0:
        input_str += f"\nRETRY ATTEMPT: {retry_count}/3\n"

    if validation_result:
        input_str += f"\n\nVALIDATION RESULT:\n{validation_result}"

    if duckdb_docs_context:
        input_str += f"\n\n{duckdb_docs_context}"

    if datasets_info and isinstance(datasets_info, dict):
        if "dataset_schema" in datasets_info:
            schema = datasets_info.get("dataset_schema")
            sample_csv = datasets_info.get("sample_data_csv")
            ds_name = datasets_info.get("user_friendly_dataset_name") or datasets_info.get(
                "dataset_name", "dataset"
            )

            if schema:
                formatted_schema = schema.format_for_prompt()
                input_str += f"\n\nDATASET INFORMATION:\n{formatted_schema}"

            if sample_csv:
                input_str += f"\n\nSAMPLE DATA ({ds_name}):\n{sample_csv}"

        elif "schemas" in datasets_info:
            schemas = datasets_info.get("schemas", [])
            if schemas:
                input_str += f"\n\nAVAILABLE DATASETS ({len(schemas)}):\n"
                for i, schema in enumerate(schemas, 1):
                    input_str += f"\n--- Dataset {i} ---\n"
                    input_str += schema.format_for_prompt()

            column_requirements = datasets_info.get("correct_column_requirements")
            if column_requirements:
                input_str += "\n\nVERIFIED COLUMN VALUES:\n"
                datasets_analysis = column_requirements.datasets
                for ds_name, analysis in datasets_analysis.items():
                    input_str += f"\nDataset: {ds_name}\n"
                    for col_analysis in analysis.columns_analyzed:
                        col_name = col_analysis.column_name
                        verified_values = col_analysis.verified_values
                        suggested_alternatives = col_analysis.suggested_alternatives

                        if verified_values:
                            exact_vals = [v.value for v in verified_values if v.found_in_database]
                            not_found_vals = [
                                v.value for v in verified_values if not v.found_in_database
                            ]

                            if exact_vals:
                                escaped_vals = [escape_value(val) for val in exact_vals]
                                input_str += (
                                    f"- {col_name} (exact matches): {', '.join(escaped_vals)}\n"
                                )
                            if not_found_vals:
                                escaped_vals = [escape_value(val) for val in not_found_vals]
                                input_str += (
                                    f"- {col_name} (not found): {', '.join(escaped_vals)}\n"
                                )

                        if suggested_alternatives:
                            for suggestion in suggested_alternatives:
                                if suggestion.found_similar_values and suggestion.similar_values:
                                    escaped_vals = [
                                        escape_value(val) for val in suggestion.similar_values
                                    ]
                                    input_str += f"- {col_name} (alternatives for '{suggestion.requested_value}'): {', '.join(escaped_vals)}\n"
                                else:
                                    input_str += f"- {col_name} (no alternatives found for '{suggestion.requested_value}')\n"

    elif dataset_info:
        input_str += f"\n\nAVAILABLE DATASETS AND SCHEMAS:\n{dataset_info}"

    if error_messages and retry_count > 0:
        input_str += "\n\nPREVIOUS ERRORS:\n"
        for error in error_messages:
            if isinstance(error, dict):
                for error_type, error_msg in error.items():
                    input_str += f"- {error_type}: {error_msg}\n"
            else:
                input_str += f"- {error}\n"

    if prev_sql_queries:
        input_str += "\n\nPREVIOUS SQL QUERIES (use as base for modifications with most recent ones at first):\n"
        for i, sql_query in enumerate(prev_sql_queries, 1):
            input_str += f"Query {i}:\n```sql\n{sql_query}\n```\n"

    return {"input": input_str}
