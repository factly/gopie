from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
)

from app.utils.prompts import escape_value
from app.workflow.graph.multi_dataset_graph.types import DatasetsInfo


def create_plan_query_prompt(**kwargs) -> list | ChatPromptTemplate:
    prompt_template = kwargs.get("prompt_template", False)
    input_content = kwargs.get("input", "")

    system_content = """
You are a DuckDB and data expert. Analyze the user's question and available datasets to determine if valid SQL queries can be generated.

## INTERNAL VALIDATION (DO NOT EXPOSE IN RESPONSE)
Before deciding on your response, internally validate:
1. Data Compatibility: Can the available datasets answer the user's question?
2. Column Availability: Are required columns present in the datasets?
3. Join Feasibility: If multiple datasets are needed, can they be properly joined?

Based on this internal validation, choose ONE response path:

## RESPONSE PATHS
Path A - Generate SQL Queries: If validation passes and datasets can fulfill the query
Path B - No-SQL Response: If datasets are insufficient, incompatible, or query cannot be answered

## DATABASE COMPATIBILITY
- SQL queries MUST be compatible with DuckDB
- Use exact dataset_name (table name) from schema, not user-friendly names
- No semicolons at end of queries
- Use double quotes for table/column names, single quotes for values

## DATASET RELATIONSHIP ANALYSIS
Related Datasets: Create a SINGLE query with appropriate JOINs
Unrelated Datasets: Create MULTIPLE independent queries

## SQL RULES
- Use EXACT column names from dataset schema
- Case-insensitive text matching: LOWER(column) = LOWER('value')
- No ILIKE or LIKE operators
- Exclude 'Total' categories and state='All India' when filtering
- Include units/unit columns when displaying values

Note: Take into account the validation result to improve the response according to the issues mentioned in the validation result.

Response Guidelines:
- If SQL can be generated: populate `sql_queries` array, leave `response_for_no_sql` empty
- If SQL cannot be generated: populate `response_for_no_sql`, leave `sql_queries` array empty
- Always include `limitations` field
- Ignore visualization requirements in user queries
"""

    human_template_str = """
{input}
"""

    if prompt_template:
        return ChatPromptTemplate.from_messages(
            [
                SystemMessage(content=system_content),
                HumanMessagePromptTemplate.from_template(human_template_str),
            ]
        )

    human_content = human_template_str.format(input=input_content)

    return [
        SystemMessage(content=system_content),
        HumanMessage(content=human_content),
    ]


def format_plan_query_input(
    user_query: str,
    datasets_info: DatasetsInfo,
    error_messages: list | None = None,
    retry_count: int = 0,
    previous_sql_queries: list | None = None,
    validation_result: str | None = None,
) -> dict:
    input_str = f"❓ USER QUERY: {user_query}\n"

    if retry_count > 0:
        input_str += f"🔄 RETRY ATTEMPT: {retry_count}/3\n"

    if validation_result:
        input_str += f"\n\n🔄 VALIDATION RESULT:\n{validation_result}"

    if datasets_info:
        schemas = datasets_info.get("schemas", [])
        if schemas:
            input_str += f"\n📊 AVAILABLE DATASETS ({len(schemas)}):\n"
            for i, schema in enumerate(schemas, 1):
                input_str += f"\n--- Dataset {i} ---\n"
                input_str += schema.format_for_prompt()

        column_requirements = datasets_info.get("correct_column_requirements")
        if column_requirements:
            input_str += "\n🔍 VERIFIED COLUMN VALUES:\n"
            datasets_analysis = column_requirements.datasets
            for dataset_name, analysis in datasets_analysis.items():
                input_str += f"\nDataset: {dataset_name}\n"
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
                            input_str += f"- {col_name} (not found): {', '.join(escaped_vals)}\n"

                    if suggested_alternatives:
                        for suggestion in suggested_alternatives:
                            if suggestion.found_similar_values and suggestion.similar_values:
                                escaped_vals = [
                                    escape_value(val) for val in suggestion.similar_values
                                ]
                                input_str += f"- {col_name} (alternatives for '{suggestion.requested_value}'): {', '.join(escaped_vals)}\n"
                            else:
                                input_str += f"- {col_name} (no alternatives found for '{suggestion.requested_value}')\n"

    if error_messages and retry_count > 0:
        input_str += "\n⚠️ PREVIOUS ERRORS:\n"
        for error in error_messages:
            for error_type, error_msg in error.items():
                input_str += f"- {error_type}: {error_msg}\n"

    if previous_sql_queries:
        input_str += "\n📝 PREVIOUS QUERIES:\n"
        for sql_query in previous_sql_queries:
            input_str += f"- {sql_query}\n"

    return {"input": input_str}
