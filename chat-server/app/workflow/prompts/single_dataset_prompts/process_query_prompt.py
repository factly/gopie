from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
)

from app.models.query import QueryResult
from app.models.schema import DatasetSchema
from app.workflow.prompts.formatters.format_query_result import (
    format_query_result,
)


def create_process_query_prompt(
    **kwargs,
) -> list[BaseMessage] | ChatPromptTemplate:
    """
    Constructs a prompt for a language model to determine whether a user's question requires SQL queries or can be answered from existing context, enforcing strict SQL formatting and response rules.

    Parameters:
        prompt_template (bool, optional): If True, returns a ChatPromptTemplate; otherwise, returns a list of BaseMessage objects.
        input (str, optional): The user's input question to include in the prompt.

    Returns:
        list[BaseMessage] | ChatPromptTemplate: The constructed prompt as either a list of messages or a prompt template, depending on the `prompt_template` flag.
    """
    prompt_template = kwargs.get("prompt_template", False)
    input_content = kwargs.get("input", "")

    system_content = """
You are a DuckDB and data expert. Analyze the user's question and determine if you need to generate SQL queries to get new data or if you can answer using available context.

INSTRUCTIONS:
1. If the user's question can be answered using the sample data or previous context, generate a response with empty SQL queries and provide a response for non-SQL queries.
2. If new data analysis is needed, generate appropriate SQL queries.
3. If the user is also asking for visualization than just ignore that and don't reply anything in context to the visualization requirements of the user.
4. Consider validation results and previous query results as context to improve over the previous query results.

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


def format_process_query_input(
    user_query: str,
    dataset_name: str,
    dataset_schema: DatasetSchema,
    rows_csv: str,
    validation_result: str | None = None,
    prev_query_result: QueryResult | None = None,
    previous_sql_queries: list | None = None,
    **kwargs,
) -> dict:
    """
    Format user query, dataset information, and sample data for prompt input.

    Combines user query, dataset schema, sample data, and optional context (previous results
    and validation) into a structured prompt string for language model processing.

    Args:
        user_query (str): The user's question to be answered
        dataset_name (str): Name of the dataset being queried
        dataset_schema (DatasetSchema): Schema object providing formatted schema information
        rows_csv (str): Sample data from the dataset in CSV format
        validation_result (str | None, optional): Validation analysis from previous query
        prev_query_result (QueryResult | None, optional): Previous query result for context
        previous_sql_queries (list | None, optional): Previously executed SQL queries
        **kwargs: Additional keyword arguments

    Returns:
        dict: Dictionary with "input" key containing the fully formatted prompt string
    """
    formatted_schema = dataset_schema.format_for_prompt()

    input_str = f"""❓ USER QUERY: {user_query}

📊 DATASET INFORMATION:
{formatted_schema}

📄 SAMPLE DATA ({dataset_name}):
{rows_csv}"""

    if validation_result:
        input_str += f"\n\n🔄 VALIDATION RESULT:\n{validation_result}"

    if prev_query_result:
        formatted_prev_result = format_query_result(prev_query_result)
        input_str += f"\n\n🔄 PREVIOUS QUERY CONTEXT:\n{formatted_prev_result}"

    if previous_sql_queries:
        input_str += "\n--- PREVIOUS SQL QUERIES ---\n"
        input_str += "Previous SQL queries:"
        for sql_query in previous_sql_queries:
            input_str += f"- {sql_query}\n"

    return {"input": input_str}
