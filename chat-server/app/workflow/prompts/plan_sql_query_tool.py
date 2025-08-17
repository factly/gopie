import json

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
You are an expert SQL analyst. Your task is to analyze natural language queries and
dataset schemas to plan appropriate SQL queries for data retrieval.

ANALYSIS PROCESS:
1. Analyze the user query to understand data requirements
2. Examine provided schemas to identify relevant tables and columns
3. Use actual dataset names (e.g., 'gq_xxxxx') from schema, NOT display names
4. Plan SQL queries needed to answer the question
5. Consider joins, aggregations, filters, and ordering requirements
6. Provide clear reasoning for your analytical approach
7. Ignore visualization requests - focus only on data retrieval

CRITICAL REQUIREMENTS:
- Always use the actual "dataset_name" field from schema in SQL queries
- Never use user-friendly display names or titles in SQL
- Ensure SQL syntax is correct and follows best practices
- For multiple queries, explain sequence and purpose of each

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


def format_sql_planning_input(user_query: str, schemas: list[dict]) -> dict:
    if schemas:
        formatted_schemas = json.dumps(schemas, indent=2)
    else:
        formatted_schemas = "No schemas available"

    formatted_input = (
        f"USER QUERY: {user_query}\n\n" f"AVAILABLE DATASETS AND SCHEMAS:\n{formatted_schemas}\n"
    )
    return {"input": formatted_input}
