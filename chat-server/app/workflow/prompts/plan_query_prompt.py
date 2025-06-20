from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage


def create_plan_query_prompt(
    user_query: str,
    formatted_datasets: Any,
    error_context: str | None = None,
    dataset_analysis_context: str | None = None,
    node_messages_context: str | None = None,
) -> list:
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
You must provide two versions of the SQL query (or queries):
1. "sql_query": A simple version for execution
2. "formatted_sql_query": A well-formatted version for UI display with:
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
            "formatted_sql_query": "the well-formatted SQL query for UI display",
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
User Query: "{user_query}"

# DATASETS INFORMATION
Selected Datasets Information:
{formatted_datasets}

# DATASET ANALYSIS RESULTS
{dataset_analysis_context}

# WORKFLOW CONTEXT
{node_messages_context}

# ERROR INFORMATION
{error_context}
"""

    return [
        SystemMessage(content=system_content),
        HumanMessage(content=human_content),
    ]
