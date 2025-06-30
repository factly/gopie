import json

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)


def create_process_query_prompt(
    **kwargs,
) -> list[BaseMessage] | ChatPromptTemplate:
    prompt_template = kwargs.get("prompt_template", False)
    input_content = kwargs.get("input", "")

    system_content = """
You are a DuckDB and data expert. Analyze the user's
question and determine if you need to generate SQL queries to get new data or
if you can answer using available context.

INSTRUCTIONS:
1. If the user's question can be answered using the sample data or previous
   context, generate a response with empty SQL queries and give response for
   non-sql queries.
2. If new data analysis is needed, generate appropriate SQL queries

RULES FOR SQL QUERIES (when needed):
- No semicolon at end of query
- Use double quotes for table/column names, single quotes for values
- Exclude rows with state='All India' when filtering/aggregating by state
- For share/percentage calculations, calculate as: (value/total)*100
- Exclude 'Total' category from categorical field calculations
- Include units/unit column when displaying value columns
- Use Levenshtein for fuzzy string matching
- Use ILIKE for case-insensitive matching
- Generate only read queries (SELECT)
- Pay careful attention to exact column names from the schema
- Use the TABLE NAME provided in the input for forming SQL queries

RESPONSE FORMAT:
Return a JSON object in one of these formats:
{{
    "sql_queries": ["<SQL query here without semicolon>", ...],
    "explanations": ["<Brief explanation for each query>", ...],
    "response_for_non_sql": "<Brief explanation for non-sql response>"
}}

Always respond with valid JSON only."""

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


def format_process_query_input(
    user_query: str,
    dataset_name: str,
    schema_json: str,
    rows_csv: str,
    error_context: str = "",
    **kwargs,
) -> dict:
    try:
        schema_info = json.loads(schema_json)

        if "error" in schema_info:
            formatted_schema = (
                f"Error retrieving schema: {schema_info['error']}"
            )
        else:
            dataset_name_from_schema = schema_info.get(
                "dataset_name", "Unknown"
            )
            dataset_description = schema_info.get(
                "dataset_description", "No description available"
            )
            user_friendly_name = schema_info.get(
                "name", dataset_name_from_schema
            )

            columns = schema_info.get("columns", [])

            formatted_schema = f"""DATASET INFORMATION:
- Name: {user_friendly_name}
- Table Name (for SQL): {dataset_name_from_schema}
- Description: {dataset_description}

COLUMNS ({len(columns)} total):"""

            for i, column in enumerate(columns, 1):
                column_name = column.get("column_name", "unknown")
                column_type = column.get("column_type", "unknown")
                column_description = column.get(
                    "column_description", "No description"
                )

                sample_values = column.get("sample_values", [])
                sample_str = ""
                if sample_values:
                    formatted_samples = [str(val) for val in sample_values[:5]]
                    sample_str = (
                        f" | Sample values: {', '.join(formatted_samples)}"
                    )
                    if len(sample_values) > 5:
                        sample_str += "..."

                stats_info = ""
                if (
                    column.get("min") is not None
                    or column.get("max") is not None
                ):
                    min_val = column.get("min")
                    max_val = column.get("max")
                    if min_val is not None and max_val is not None:
                        stats_info = f" | Range: {min_val} to {max_val}"

                unique_count = column.get("approx_unique")
                if unique_count is not None:
                    stats_info += f" | ~{unique_count} unique values"

                formatted_schema += f"""
{i}. {column_name} ({column_type})
   Description: {column_description}{sample_str}{stats_info}"""

    except (json.JSONDecodeError, Exception):
        formatted_schema = f"TABLE SCHEMA IN JSON:\n{schema_json}"

    formatted_input = f"""
USER QUESTION: {user_query}

DATASET INFORMATION:
{formatted_schema}

DATASET NAME: {dataset_name}

SAMPLE DATA (50 ROWS) IN CSV:
---------------------
{rows_csv}
---------------------

{error_context}"""

    return {"input": formatted_input}
