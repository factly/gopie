from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
)

from app.models.schema import DatasetSchema


def regenerate_fuzzy_values_prompt(**kwargs) -> list[BaseMessage] | ChatPromptTemplate:
    prompt_template = kwargs.get("prompt_template", False)
    input_content = kwargs.get("input", "")

    system_content = """
TASK: Generate alternative fuzzy values for column searches that failed to find matches.

CONTEXT:
You are helping to find relevant data in a database. Previous attempts to match column values using fuzzy search have failed.
Your job is to generate ALTERNATIVE fuzzy values that might better match the actual data in the database.

INSTRUCTIONS:

1. ANALYZE THE FAILURE:
   * Review the failed fuzzy values and understand why they might not have matched
   * Consider alternative terms, synonyms, abbreviations, or different phrasings
   * Think about how users might have entered the data differently

2. GENERATE NEW FUZZY VALUES:
   * Provide NEW fuzzy values that are different from the previously attempted ones
   * Generate values that are more likely to match actual database entries
   * Consider:
     - Synonyms and related terms
     - Abbreviated forms or full forms
     - Common misspellings or variations
     - Different word orders or phrasings
     - Singular/plural variations
   * DO NOT repeat the same fuzzy values that already failed
   * Provide 2-3 alternative fuzzy values per failed column

3. VALUE GUIDELINES:
   * Only generate fuzzy values for TEXT/STRING/VARCHAR columns
   * Do NOT generate fuzzy values for INTEGER, BIGINT, FLOAT, BOOLEAN, DATE, TIMESTAMP or other non-string columns—omit those columns from your output
   * Provide REAL searchable terms, NOT placeholders
   * Focus on meaningful text values that can be used for substring matching
   * Avoid numeric or nonsensical values
   * DO NOT include system identifiers like project_id or dataset_id

4. OUTPUT FORMAT:
   * Return ONLY the datasets and columns that had failures (and are TEXT/STRING/VARCHAR)
   * Omit failed columns that are INTEGER, BIGINT, FLOAT, BOOLEAN, DATE, TIMESTAMP or other non-string types—do not include them in your output
   * For each remaining failed column, provide NEW fuzzy values to try
   * Include a reasoning field explaining your alternative approach

IMPORTANT:
* Be creative with alternatives - think outside the box
* Consider the context of the user query and dataset description
* Focus on values that are more generic or more specific as needed
* Your goal is to help find matching data that might exist with different terminology
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


def format_regenerate_fuzzy_values_input(
    user_query: str,
    dataset_schemas: list[DatasetSchema],
    failed_fuzzy_searches: dict,
    retry_attempt: int,
) -> dict:
    """
    Format the input for regenerating fuzzy values.

    Args:
        user_query: The original user query
        dataset_schemas: List of dataset schemas for context
        failed_fuzzy_searches: Dictionary mapping dataset -> column -> failed fuzzy values
        retry_attempt: Current retry attempt number (1-3)

    Returns:
        dict: Formatted input dictionary
    """
    input_str = f"USER QUERY: {user_query}"
    input_str += f"\n\nRETRY ATTEMPT: {retry_attempt} of 3"
    input_str += "\n\n=== FAILED FUZZY VALUE SEARCHES ==="

    for dataset_name, columns_data in failed_fuzzy_searches.items():
        input_str += f"\n\nDATASET: {dataset_name}"

        matching_schema = next((s for s in dataset_schemas if s.dataset_name == dataset_name), None)
        if matching_schema:
            input_str += f"\nDescription: {matching_schema.dataset_description}"
            input_str += f"\nColumns available: {', '.join([col.column_name for col in matching_schema.columns])}"

        for column_name, failed_values in columns_data.items():
            col = next(
                (c for c in matching_schema.columns if c.column_name == column_name),
                None,
            ) if matching_schema else None
            col_type = f" ({col.column_type})" if col else ""
            input_str += f"\n\n  Column: {column_name}{col_type}"

            failed_items = []
            for item in failed_values:
                if isinstance(item, dict):
                    value = item.get("value", str(item))
                    error = item.get("error")
                    if error:
                        failed_items.append(f"{value} (Error: {error})")
                    else:
                        failed_items.append(value)
                else:
                    failed_items.append(str(item))

            input_str += f"\n  Failed fuzzy values: {', '.join(failed_items)}"
            input_str += "\n  ❌ No similar values found in database for any of these terms"

    input_str += "\n\n=== YOUR TASK ==="
    input_str += "\nGenerate NEW alternative fuzzy values for each failed column."
    input_str += "\nThink creatively about synonyms, variations, and alternative phrasings."
    input_str += (
        "\nProvide 2-3 new fuzzy values per column that are DIFFERENT from the failed attempts."
    )

    return {"input": input_str}
