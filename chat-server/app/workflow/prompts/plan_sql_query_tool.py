import json

from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
)


def create_sql_planning_prompt(
    **kwargs,
) -> list[BaseMessage] | ChatPromptTemplate:
    prompt_template = kwargs.get("prompt_template", False)
    input_content = kwargs.get("input", "")

    system_content = """You are an expert SQL analyst. Given a user's natural language
query and dataset schemas, plan the appropriate SQL queries to answer their
question.

INSTRUCTIONS:
1. Analyze the user query to understand what data they need
2. Examine the provided schemas to identify relevant tables and columns
3. Use the actual dataset names (like 'gq_xxxxx') from the schema in your SQL,
   NOT the user-friendly display names
4. Plan the SQL query/queries needed to answer the question
5. Consider joins, aggregations, filters, and ordering as needed
6. Provide clear reasoning for your approach

OUTPUT FORMAT (JSON):
{
    "reasoning": "Step-by-step explanation of your thought process",
    "sql_queries": ["list of executable SQL queries"],
    "tables_used": ["list of table names used"],
    "expected_result": "description of what the query results contain",
    "limitations": "any assumptions, limitations, or considerations"
}

CRITICAL: Always use the actual dataset name field from the schema in your
SQL queries, never use display names or titles. Look for fields like
"dataset_name" or similar in the schema.

Ensure your SQL is syntactically correct and follows best practices. If
multiple queries are needed, explain the sequence and purpose of each."""

    human_template_str = "{input}"

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


def format_sql_planning_input(user_query: str, schemas: list[dict]) -> dict:
    if schemas:
        formatted_schemas = json.dumps(schemas, indent=2)
    formatted_input = (
        f"USER QUERY: {user_query}\n\nAVAILABLE DATASETS AND SCHEMAS:\n{formatted_schemas}\n"
    )
    return {"input": formatted_input}
