from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
)

from app.models.schema import DatasetSchema


def create_identify_datasets_prompt(
    **kwargs,
) -> list[BaseMessage] | ChatPromptTemplate:
    """
    Constructs a prompt for selecting relevant datasets and specifying column assumptions based on user queries and dataset schemas.

    Depending on the `prompt_template` argument, returns either a `ChatPromptTemplate` for further formatting or a list of `SystemMessage` and `HumanMessage` objects ready for use. The prompt includes detailed instructions for evaluating datasets from two sources: relevant datasets from chat history and semantic searched datasets. The LLM must evaluate all datasets and select the most relevant ones, regardless of their source. Guidelines are provided for column value assumptions (with strict rules for string vs. non-string columns), and the expected JSON response format for downstream processing.

    Parameters:
        prompt_template (bool, optional): If True, returns a `ChatPromptTemplate` object; otherwise, returns formatted message objects.
        input (str, optional): The user input or query to be included in the prompt.

    Returns:
        list[BaseMessage] | ChatPromptTemplate: The constructed prompt as either a message list or a prompt template, depending on the `prompt_template` flag.
    """
    prompt_template = kwargs.get("prompt_template", False)
    input_content = kwargs.get("input", "")

    system_content = """
TASK: Process dataset schemas and provide column assumptions for analysis.

INSTRUCTIONS:

There are TWO types of datasets provided:

1. RELEVANT DATASETS (From Chat History):
   * These datasets were used in previous queries from the chat history
   * These are NOT auto-selected - you must evaluate their relevance to the current query
   * Consider these datasets alongside semantic searched datasets when making your selection
   * Include them in your selection only if they are relevant to answering the current user query

2. SEMANTIC SEARCHED DATASETS (From Vector Search):
   * These datasets were found through semantic search based on the current query
   * Choose the dataset(s) that best match the user query based on usefulness and relevance
   * You can select multiple datasets if needed
   * Always refer to datasets by their "Table SQL Name"
   * IMPORTANT: The query type and confidence score were determined by a previous LLM step.
     Do NOT rely solely on the query type or confidence score - use your own reasoning to determine if datasets are useful
   * If datasets are relevant and useful for answering the query, select them REGARDLESS of query type or confidence score
   * Your primary goal is to select datasets that help answer the user's question effectively

DATASET SELECTION:
* Evaluate ALL datasets from BOTH sources (relevant + semantic searched)
* Select the TOP MOST RELEVANT datasets that will help answer the user's query
* You can choose datasets from either or both categories
* Consider combining datasets if they provide complementary information
* Always prioritize relevance and usefulness over the source of the dataset

COLUMN ASSUMPTIONS:
* Provide column assumptions for ALL datasets that you select for use
* List ONLY the columns needed for the query
* IMPORTANT: Only provide value assumptions (exact_values/fuzzy_values) for TEXT/STRING/VARCHAR columns that support fuzzy matching
* For NON-STRING columns (BIGINT, INTEGER, FLOAT, DATE, TIMESTAMP, BOOLEAN, etc.), include the column in the list but DO NOT provide exact_values or fuzzy_values
* For string columns ONLY, provide:
    - "exact_values": actual values seen in sample_data that match the query terms
    - "fuzzy_values": search terms or substrings to help match the column values; provide meaningful text values that can be used to match the column values in that dataset, avoiding numeric or unprocessable values

VALUE GUIDELINES:
* Provide REAL values (e.g., "finance", "Alice") NOT placeholders
* Both exact_values and fuzzy_values refer to actual data values, not column names
* Include ONLY string/text/varchar columns in the values list
* DO NOT provide exact_values or fuzzy_values for numeric columns (BIGINT, INTEGER, FLOAT), date columns (DATE, TIMESTAMP), or boolean columns
* DO NOT include numerical or nonsensical values in fuzzy_values that cannot be used to effectively match data
* Only use exact_values when completely confident the value exists in sample_data
* For non-string columns, simply include the column name without any value assumptions to avoid type errors in SQL operations

NODE MESSAGE:
* Include a brief informative message to pass to subsequent nodes
* This message should describe what datasets were selected and why
* Mention whether datasets came from chat history (relevant) or semantic search
* If datasets from chat history were not selected, briefly explain why
* Be concise but informative - this will help guide later processing

IMPORTANT:
* selected_dataset should contain the best datasets chosen from ALL available sources
* column_assumptions should include ALL selected datasets
* Always use the dataset "Table SQL Name" field (not "name" field)
* Only use exact_values when completely confident the value exists
* Make your node_message informative providing context on dataset sources and selection rationale
* For numeric, date, boolean, or other non-string columns: include them in column_assumptions but omit exact_values and fuzzy_values to prevent SQL type errors
* Take into account the validation result to improve according to the issues mentioned in the validation result.
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


def format_identify_datasets_input(
    user_query: str,
    relevant_dataset_schemas: list[DatasetSchema] = [],
    semantic_searched_datasets: list[DatasetSchema] = [],
    validation_result: str | None = None,
) -> dict:
    input_str = f"USER QUERY: {user_query}"

    input_str += (
        f"\n\n=== RELEVANT DATASETS (From Chat History): {len(relevant_dataset_schemas)} ==="
    )

    if validation_result:
        input_str += f"\n\n🔄 VALIDATION RESULT:\n{validation_result}"

    if relevant_dataset_schemas:
        input_str += "\nThese datasets were used in previous queries from chat history."
        input_str += "\nEvaluate their relevance to the current query and include them in your selection if useful."

        for i, schema in enumerate(relevant_dataset_schemas, 1):
            input_str += f"\n\n--- RELEVANT DATASET {i} ---"
            input_str += f"\n{schema.format_for_prompt()}"
    else:
        input_str += "\nNone available"

    input_str += f"\n\n=== SEMANTIC SEARCHED DATASETS (From Vector Search): {len(semantic_searched_datasets)} ==="

    if semantic_searched_datasets:
        input_str += "\nThese datasets were found through semantic search based on your query."
        input_str += "\nEvaluate their relevance and include them in your selection if useful."

        for i, schema in enumerate(semantic_searched_datasets, 1):
            input_str += f"\n\n--- SEMANTIC DATASET {i} ---"
            input_str += f"\n{schema.format_for_prompt()}"
    else:
        input_str += "\nNone available"

    if not relevant_dataset_schemas and not semantic_searched_datasets:
        input_str += "\n\n⚠️  No datasets available for analysis"

    return {"input": input_str}
