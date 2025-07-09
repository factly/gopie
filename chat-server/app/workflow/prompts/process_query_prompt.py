from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
)

from app.models.schema import ColumnSchema, DatasetSchema


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
{
    "sql_queries": ["<SQL query here without semicolon>", ...],
    "explanations": ["<Brief explanation for each query>", ...],
    "response_for_non_sql": "<Brief explanation for non-sql response>"
}

Always respond with valid JSON only."""

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


def format_process_query_input(
    user_query: str,
    dataset_name: str,
    dataset_schema: DatasetSchema,
    rows_csv: str,
    prev_query_result: dict | None = None,
    validation_result: dict | None = None,
    **kwargs,
) -> dict:
    formatted_input = f"USER QUESTION: {user_query}\n\n"
    formatted_schema = dataset_schema.format_for_prompt(
        columns_fields_to_exclude=["avg", "count", "std"]
    )
    formatted_input += f"DATASET INFORMATION:\n{formatted_schema}\n\n"
    formatted_input += f"DATASET NAME: {dataset_name}\n\n"
    formatted_input += f"SAMPLE DATA (50 ROWS) IN CSV:\n"
    formatted_input += "-" * 20 + f"\n{rows_csv}\n" + "-" * 20 + "\n"
    formatted_input += f"{error_context}"
    return {"input": formatted_input}
