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

OUTPUT FORMAT (JSON):
{
    "reasoning": "Step-by-step explanation of your analytical approach",
    "sql_queries": ["list of executable SQL queries"],
    "tables_used": ["list of actual table names used"],
    "expected_result": "description of what the query results will contain",
    "limitations": "assumptions, limitations, or important considerations"
}

QUALITY STANDARDS:
- SQL must be syntactically correct and executable
- Queries should be optimized for performance
- Include proper error handling considerations
- Document any assumptions made about data structure or content
- Ignore visualization requirements in user queries
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
