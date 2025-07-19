from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
)

from app.workflow.graph.multi_dataset_graph.types import DatasetsInfo


def create_plan_query_prompt(**kwargs) -> list | ChatPromptTemplate:
    prompt_template = kwargs.get("prompt_template", False)
    input_content = kwargs.get("input", "")

    system_content = """
Given the following natural language query and detailed information about multiple datasets, create appropriate SQL query or queries.

CAUTION: If the user is also asking for visualization than just ignore that and don't reply anything in context to the visualization requirements of the user.

# DATABASE COMPATIBILITY REQUIREMENTS
IMPORTANT:
- Generated SQL queries MUST be compatible with DuckDB SQL execution engine.
- Avoid PostgreSQL-specific syntax and functions.

# DATASET NAMING GUIDELINES
IMPORTANT - DATASET NAMING:
- In your SQL query, you MUST use the dataset_name (table name) provided in the schema.
- This is the actual table name used in the database.
- DO NOT use the user-friendly name in SQL queries.

# CASE SENSITIVITY GUIDELINES
- When comparing column values (not column names), use LOWER() function for case-insensitive matching.
- Example: WHERE LOWER(column_name) = LOWER('value').
- Do NOT use LOWER() for column names or table/dataset names.

# DATASET RELATIONSHIP ASSESSMENT
1. ANALYZE whether the selected datasets can be related through common fields:
   - Look for matching column names, primary/foreign keys, or semantic relationships.
   - Determine if JOIN operations are possible between datasets.
2. DECISION POINT:
   a) If datasets ARE RELATED:
      - Create a SINGLE SQL query using appropriate JOINs.
      - Use the most efficient join type (INNER, LEFT, etc.).
   b) If datasets are NOT RELATED (no sensible join possible):
      - Create MULTIPLE independent SQL queries (one per dataset).
      - Each query should extract the relevant information from its dataset.

# QUERY DEVELOPMENT GUIDELINES (IMPORTANT)
1. Use the EXACT column names as shown in the dataset information.
2. Create a query that directly addresses the user's question.
3. If the user's query refers to a time period that doesn't match the dataset format (e.g., asking for 2018 when dataset uses 2018-19), adapt accordingly.
4. Make sure to handle column names correctly, matching the exact names in the dataset metadata.
5. Use the sample data as reference for the data format and values.
6. If the query requires joining multiple datasets, make sure to:
   - Use appropriate join conditions.
   - Handle potentially conflicting column names.
   - Specify table aliases if needed.
   - Consider the relationship between datasets.
7. For text comparisons, use LOWER() function on both sides to ensure case-insensitive matching.
8. Never use ILIKE, LIKE operator while generating SQL query.

# SQL FORMATTING REQUIREMENTS
You must provide a well-formatted version of the SQL query for UI display with:
- SQL keywords in UPPERCASE.
- Each major clause on a new line.
- Proper indentation for readability.
- Consistent spacing around operators.

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
Note: If datasets are related and you only need one query, "sql_queries" should contain only one element. If datasets aren't related, include multiple queries in the "sql_queries" array, one for each dataset needed.
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
    node_messages: dict | None = None,
) -> dict:
    input_str = f"USER QUERY: {user_query}\n"

    if retry_count > 0:
        input_str += f"RETRY ATTEMPT: {retry_count}/3\n"

    if datasets_info:
        input_str += "\n--- DATASETS INFORMATION ---\n"

        schemas = datasets_info.get("schemas", [])
        if schemas:
            input_str += f"\nDataset Schemas ({len(schemas)}):\n"

            for i, schema in enumerate(schemas, 1):
                schema_section = f"\n--- DATASET {i}: ---\n"
                schema_section += schema.format_for_prompt()
                input_str += schema_section + "\n"

        column_requirements = datasets_info["correct_column_requirements"]
        if column_requirements:
            input_str += "\n--- COLUMN VALUE ANALYSIS ---\n"
            input_str += "Verified column values from database analysis:"

            datasets_analysis = column_requirements.datasets
            for dataset_name, analysis in datasets_analysis.items():
                input_str += f"\nDataset: {dataset_name}\n"
                columns_analyzed = analysis.columns_analyzed

                for col_analysis in columns_analyzed:
                    col_name = col_analysis.column_name
                    input_str += f"- Column: {col_name}\n"

                    verified_values = col_analysis.verified_values
                    if verified_values:
                        exact_vals = [v.value for v in verified_values if v.found_in_database]
                        if exact_vals:
                            input_str += f"  ✓ Exact matches found: {', '.join(exact_vals)}"

                    suggested_alternatives = col_analysis.suggested_alternatives
                    if suggested_alternatives:
                        for alt in suggested_alternatives:
                            if alt.found_similar_values:
                                similar_vals = alt.similar_values[:5]
                                if similar_vals:
                                    input_str += f"  ⚠ Similar values for '{alt.requested_value}': {', '.join(similar_vals)}"

    if error_messages and retry_count > 0:
        input_str += "\n--- PREVIOUS ERRORS ---\n"
        input_str += f"Previous attempt {retry_count} failed. Errors encountered:"
        for error in error_messages:
            for error_type, error_msg in error.items():
                input_str += f"- {error_type}: {error_msg}\n"
        input_str += "Please analyze these errors and generate corrected SQL queries."

    if node_messages:
        input_str += "\n--- WORKFLOW CONTEXT ---"
        input_str += "Previous workflow steps information:"
        for node, message in node_messages.items():
            if isinstance(message, dict):
                input_str += f"- {node}:"
                for key, value in message.items():
                    input_str += f"  {key}: {value}"
            else:
                input_str += f"- {node}: {message}"

    return {
        "input": input_str,
    }
