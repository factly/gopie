from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
)

from app.utils.prompts import escape_value
from app.workflow.graph.single_dataset_graph.types import SingleDatasetInfo
from app.workflow.graph.sql_planner_graph.types import DatasetsInfo
from app.workflow.prompts.db_prompts import (
    get_db_name,
    get_expert_role,
    get_sql_compatibility_instructions,
)
from app.workflow.prompts.formatters.format_prompt_for_langsmith import (
    langsmith_compatible,
)


def generate_sql_prompt(**kwargs) -> list[BaseMessage] | ChatPromptTemplate:
    prompt_template = kwargs.get("prompt_template", False)
    input_content = kwargs.get("input", "")

    db_name = get_db_name()
    expert_role = get_expert_role()
    db_compatibility = get_sql_compatibility_instructions()

    system_content = f"""
{expert_role} Analyze the user's question and available datasets to determine if valid SQL queries can be generated.

## DECISION FRAMEWORK

### Step 1: Internal Validation (Do Not Expose)
Before responding, internally validate:
1. **Data Compatibility**: Can the available dataset(s) answer the user's question?
2. **Column Availability**: Are required columns present in the dataset schema(s)?
3. **Join Feasibility**: If multiple datasets, can they be properly joined?
4. **Context Sufficiency**: Can the question be answered from sample data or previous results?

### Step 2: Choose Response Path
Based on validation, select ONE path:

**Path A - Generate SQL Queries**: If datasets can fulfill the query
**Path B - No-SQL Response**: If:
- Datasets are insufficient or incompatible
- Query can be answered from existing context (sample data, previous results)
- Required columns or data are missing

## DATABASE & QUERY RULES

### {db_name} Compatibility
{db_compatibility}
- Generate **only read queries** (SELECT statements)

### Column & Table Usage
- Use **EXACT column names** from dataset schema (case-sensitive)
- Pay careful attention to provided TABLE NAME for forming SQL queries
- Include units/unit columns when displaying value columns
- **NEVER use** project_id, dataset_id, or internal system identifiers in WHERE clauses

### Text Matching & Filtering
- **Case-insensitive matching**: Use `LOWER(column) = LOWER('value')`
- **No ILIKE or LIKE operators**

### Calculations & Aggregations
- For **share/percentage** calculations: `(value/total)*100`
- When using **summarize** command: Only for explicit statistical/summary requests

### Database-Specific Syntax
- Use {db_name} documentation to plan and generate the sql queries

### Multiple Datasets
**Related Datasets** (can be joined): Create a **SINGLE query with JOINs**
  - Look for common columns
  - Use appropriate JOIN type
  - Combine into one result table

**Unrelated Datasets** (no common join keys): Create **MULTIPLE independent queries**
  - Each query returns separate results
  - Cannot be combined into single table

## CONTEXT HANDLING

### Previous SQL Queries (For Modifications)
- When `[SQL_MODIFICATION: <type>]` is present, PREVIOUS SQL QUERIES are provided
- These are the BASE queries to modify - do NOT regenerate from scratch
- Apply the requested modification type to these queries
- Preserve query logic while making requested changes

### Validation Results
- If validation results are provided, **improve** previous queries based on issues mentioned
- Address specific problems identified in validation

### Previous subuery context
- These are the results of previously generated subqueries that can be used to answer the current query or as context for generating SQL queries. Use this information strategically to determine if SQL generation is needed or if the question can be answered from this context.

### Error Messages (Retries)
- If error messages are provided, **learn from mistakes**
- Adjust queries to avoid previous errors

## SPECIAL INSTRUCTIONS
- **Ignore** visualization requirements in user queries
- **Always** include `limitations` field
- Keep explanations **concise** and **technical**
- Keep user_friendly_response **short** and **non-technical**
- Focus on **business data** columns, not technical metadata
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
    previous_subquery_context: str | None = None,
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
            ds_name = schema.name if schema else "dataset"

            if schema:
                formatted_schema = schema.format_for_prompt()
                input_str += f"\n\nDATASET INFORMATION:\n{formatted_schema}"

            if sample_csv:
                input_str += f"\n\nSAMPLE DATA ({ds_name}):\n{sample_csv}"

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

    if previous_subquery_context:
        input_str += f"\n\n{previous_subquery_context}"

    if prev_sql_queries:
        input_str += "\n\nPREVIOUS SQL QUERIES (use as base for modifications with most recent ones at first):\n"
        for i, sql_query in enumerate(prev_sql_queries, 1):
            input_str += f"Query {i}:\n```sql\n{sql_query}\n```\n"

    return {"input": input_str}
