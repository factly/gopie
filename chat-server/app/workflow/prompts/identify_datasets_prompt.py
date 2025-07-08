import json

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)

from app.models.schema import ColumnSchema, DatasetSchema


def create_identify_datasets_prompt(**kwargs) -> list | ChatPromptTemplate:
    prompt_template = kwargs.get("prompt_template", False)
    input_content = kwargs.get("input", "")

    system_content = """
TASK: Process dataset schemas and provide column assumptions for analysis.

INSTRUCTIONS:

There are TWO types of datasets provided:

1. REQUIRED DATASETS (Auto-Selected):
   * These datasets are ALREADY SELECTED and will be used automatically
   * You do NOT need to choose whether to include them
   * These will be part of your final analysis

2. SEMANTIC SEARCHED DATASETS (Need Selection):
   * Choose the dataset(s) that best match the user query based on usefulness and relevance
   * You can select multiple datasets if needed
   * Always refer to datasets by their "Table SQL Name"
   * IMPORTANT: The query type and confidence score were determined by a previous LLM step.
     Do NOT rely solely on the query type or confidence score - use your own reasoning to determine if datasets are useful
   * If datasets are relevant and useful for answering the query, select them REGARDLESS of query type or confidence score
   * Your primary goal is to select datasets that help answer the user's question effectively

COLUMN ASSUMPTIONS:
* Provide column assumptions for ALL datasets that will be used (required datasets + selected datasets from semantic search)
* List ONLY the columns needed for the query
* For string columns ONLY, provide:
    - "exact_values": actual values seen in sample_data that match the query terms
    - "fuzzy_values": search terms or substrings to help match the column values; provide meaningful text values that can be used to match the column values in that dataset, avoiding numeric or unprocessable values

VALUE GUIDELINES:
* Provide REAL values (e.g., "finance", "Alice") NOT placeholders
* Both exact_values and fuzzy_values refer to actual data values, not column names
* Include ONLY string columns in the values list
* DO NOT include numerical or nonsensical values in fuzzy_values that cannot be used to effectively match data
* Only use exact_values when completely confident the value exists in sample_data

NODE MESSAGE:
* Include a brief informative message to pass to subsequent nodes
* This message should describe what datasets were selected (from semantic search) and why
* Mention the required datasets that are automatically included
* If no additional datasets were selected from semantic search, explain why
* Be concise but informative - this will help guide later processing

FORMAT YOUR RESPONSE AS JSON:
{{
    "selected_dataset": ["dataset_name1", "dataset_name2", ...],  // Only from SEMANTIC SEARCHED datasets
    "reasoning": "1-2 sentences explaining why these datasets were selected from semantic search",
    "column_assumptions": [
        {{
            "dataset": "dataset_name1",  // Can be from REQUIRED or SELECTED datasets
            "columns": [
                {{
                    "name": "column_name",
                    "exact_values": ["value1", ...],
                    "fuzzy_values": ["value2", ...]
                }}
            ]
        }}
    ],
    "node_message": "Brief message about all datasets (required + selected) and their relevance to the query"
}}

IMPORTANT:
* selected_dataset should ONLY contain datasets chosen from semantic searched datasets
* column_assumptions should include ALL datasets (both required and selected)
* Always use the dataset "Table SQL Name" field (not "name" field)
* Only use exact_values when completely confident the value exists
* Make your node_message informative providing context on all datasets being used
"""

    human_template_str = """
{input}
"""

    if prompt_template:
        return ChatPromptTemplate.from_messages(
            [
                SystemMessagePromptTemplate.from_template(system_content),
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
    required_dataset_schemas: list[DatasetSchema] = [],
    semantic_searched_datasets: list[DatasetSchema] = [],
    confidence_score: float | None = None,
    query_type: str | None = None,
) -> dict:
    input_str = ""
    input_str += f"USER QUERY: {user_query}\n\n"

    if query_type:
        input_str += f"QUERY TYPE: {query_type}\n\n"

    if confidence_score is not None:
        input_str += f"CONFIDENCE SCORE: {confidence_score}/10\n\n"

    if required_dataset_schemas:
        input_str += f"\n=== REQUIRED DATASETS (Auto-Selected): {len(required_dataset_schemas)} ===\n"
        input_str += "These datasets are ALREADY SELECTED and will be used automatically.\n"
        input_str += "Provide column assumptions for these datasets.\n"
        for i, schema in enumerate(required_dataset_schemas, 1):
            input_str += f"--- REQUIRED DATASET {i} ---\n"
            input_str += schema.format_for_prompt()
    else:
        input_str += "=== REQUIRED DATASETS: None ===\n"

    if semantic_searched_datasets:
        input_str += f"\n=== SEMANTIC SEARCHED DATASETS (Choose from these): {len(semantic_searched_datasets)} ===\n"
        input_str += "SELECT the most relevant datasets from these options:\n"
        for i, schema in enumerate(semantic_searched_datasets, 1):
            input_str += f"\n--- AVAILABLE DATASET {i} ---\n"
            input_str += schema.format_for_prompt()
    else:
        input_str += "=== SEMANTIC SEARCHED DATASETS: None available ===\n"
    if not required_dataset_schemas and not semantic_searched_datasets:
        input_str += "\nNo datasets available for analysis\n"
    return {"input": input_str}
