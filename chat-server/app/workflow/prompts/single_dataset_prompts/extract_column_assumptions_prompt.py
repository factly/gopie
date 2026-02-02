from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
)

from app.models.schema import DatasetSchema


def extract_column_assumptions_prompt(**kwargs) -> list[BaseMessage] | ChatPromptTemplate:
    """
    Constructs a prompt for extracting column assumptions from a user query for a single dataset.

    This prompt analyzes the user's query and identifies which columns are referenced along with
    their expected values, enabling fuzzy matching and validation.
    """
    prompt_template = kwargs.get("prompt_template", False)
    input_content = kwargs.get("input", "")

    system_content = """
TASK: Analyze the user query and extract column assumptions for fuzzy value matching.

CONTEXT:
You are analyzing a query against a single dataset. Your job is to identify which columns the user is referencing
and what values they are looking for in those columns. This information will be used for fuzzy matching to find
relevant data even when exact matches don't exist.

INSTRUCTIONS:

1. ANALYZE THE QUERY:
   * Identify which columns from the dataset schema are referenced in the user's query
   * Determine what values the user is looking for in those columns
   * Consider both explicit mentions and implicit references

2. COLUMN SELECTION:
   * Include ONLY columns where you have values to validate (exact_values OR fuzzy_values)
   * DO NOT include columns with empty values for both exact_values and fuzzy_values
   * Focus on TEXT/STRING/VARCHAR columns that need fuzzy matching
   * DO NOT include numeric, date, boolean, or other non-string columns

3. VALUE ASSUMPTIONS (CRITICAL RULES):
   * "exact_values": values from sample_data that EXACTLY match what the user is looking for
   * "fuzzy_values": ONLY for terms that are NOT in exact_values - used for fuzzy search
   * If a value is in exact_values, DO NOT add variations of it to fuzzy_values
   * fuzzy_values should be for ADDITIONAL search terms, not alternatives to exact values

4. VALUE GUIDELINES:
   * Provide REAL values (e.g., "finance", "Alice") NOT placeholders
   * Only use exact_values when you see the value in the sample_data
   * Use fuzzy_values ONLY for terms that don't have exact matches
   * DO NOT include project_id, dataset_id, or system identifiers

5. EXAMPLES:

Query: "Show me all employees in the finance department"
Dataset has: department (VARCHAR), employee_id (BIGINT)
Sample data shows: department values include "Finance", "HR", "Engineering"

Correct response (exact match found, no fuzzy needed):
{
  "column_assumptions": [
    {
      "dataset": "employees_table",
      "columns": [
        {
          "name": "department",
          "exact_values": ["Finance"],
          "fuzzy_values": []
        }
      ]
    }
  ]
}

Query: "Find orders with status completed"
Dataset has: status (VARCHAR), order_id (BIGINT)
Sample data shows: status values include "Complete", "Pending", "Cancelled"

Correct response (no exact match, use fuzzy):
{
  "column_assumptions": [
    {
      "dataset": "orders_table",
      "columns": [
        {
          "name": "status",
          "exact_values": [],
          "fuzzy_values": ["completed", "complete"]
        }
      ]
    }
  ]
}

Query: "Show sales for fiscal year 2021-22"
Sample data shows: fiscal_year values include "2021-22", "2022-23"

Correct response (exact match found):
{
  "column_assumptions": [
    {
      "dataset": "sales_table",
      "columns": [
        {
          "name": "fiscal_year",
          "exact_values": ["2021-22"],
          "fuzzy_values": []
        }
      ]
    }
  ]
}

IMPORTANT:
* If the query doesn't reference specific column values, return empty column_assumptions
* Always use the dataset's "Table SQL Name" field
* NEVER include columns where both exact_values AND fuzzy_values are empty
* If exact match exists, DO NOT add fuzzy variations of the same value
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


def format_extract_column_assumptions_input(
    user_query: str,
    dataset_schema: DatasetSchema,
) -> dict:
    """Format the input for the column assumptions extraction prompt."""
    input_str = f"USER QUERY: {user_query}"
    input_str += f"\n\n=== DATASET SCHEMA ===\n{dataset_schema.format_for_prompt()}"

    return {"input": input_str}
