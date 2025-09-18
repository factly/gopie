from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
)

from app.workflow.prompts.formatters.format_prompt_for_langsmith import (
    langsmith_compatible,
)


def create_sql_planning_prompt(
    **kwargs,
) -> list[BaseMessage] | ChatPromptTemplate:
    prompt_template = kwargs.get("prompt_template", False)
    input_content = kwargs.get("input", "")

    system_content = """
You are a DuckDB and data expert. Analyze the user's question and available datasets to determine if valid SQL queries can be generated.

## RESPONSE PATHS
Path A - Generate SQL Queries: If and only if the user query can be answered by generating sql query from the provided datasets info
Path B - No-SQL Response: If datasets are insufficient, incompatible, or query cannot be answered

## DATABASE COMPATIBILITY
- SQL queries MUST be compatible with DuckDB
- Use exact dataset_name (table name) from schema, not user-friendly names
- No semicolons at end of queries
- Use double quotes for table/column names, single quotes for values

## SQL RULES
- Use EXACT column names from dataset schema
- Case-insensitive text matching: LOWER(column) = LOWER('value')
- No ILIKE or LIKE operators
- Exclude 'Total' categories and state='All India' when filtering
- Include units/unit columns when displaying values

OUTPUT FORMAT (JSON):
{
  "sql_queries": [
    {
      "sql_query": "SQL query without semicolon, compatible with DuckDB",
      "explanation": "concise explanation including: Query strategy (e.g., filtering by X to get Y),
        key columns used and their data types, table metadata (table name, what data it contains),
        JOIN strategy if multiple tables, and expected result format",
      "tables_used": [list of table names used in the sql query]
    }
  ],
  "response_for_no_sql": "Clear explanation when SQL queries cannot be generated",
  "user_friendly_response": "",
  "limitations": "Any constraints or assumptions in the analysis"
}

Response Guidelines:
- If SQL can be generated: populate `sql_queries` array, leave `response_for_no_sql` empty
- If SQL cannot be generated: populate `response_for_no_sql`, leave `sql_queries` array empty
- If User asked for summarised insights/statistics from data, you can use `summarize` command in SQL
- Ignore visualization requirements in user queries
- Always include `limitations` field
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


def format_sql_planning_input(user_query: str, dataset_info: str) -> dict:
    formatted_input = (
        f"USER QUERY: {user_query}\n\nAVAILABLE DATASETS AND SCHEMAS:\n{dataset_info}\n"
    )
    return {"input": formatted_input}
