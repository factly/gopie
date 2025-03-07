import os
from src.lib.graph.types import IntermediateStep, ErrorMessage, State
from typing import Dict, Any, List
import json
from src.lib.config.langchain_config import lc
from langchain_core.output_parsers import JsonOutputParser
from src.utils.dataset_info import get_dataset_preview

def create_llm_prompt(user_query: str, available_datasets: List[Dict[str, Any]]) -> str:
    """Create a prompt for the LLM to identify the relevant dataset and required columns"""
    return f"""
        You are an AI assistant specialized in data analysis. Your role is to help users analyze data by identifying relevant datasets and column values.

        USER QUERY:
        "{user_query}"

        AVAILABLE DATASETS:
        {json.dumps(available_datasets, indent=2)}

        INSTRUCTIONS:
        1. This is a data analysis query that needs dataset analysis.

        2. Based on the user query, determine which of the available datasets best matches the user's needs.
           - Consider the content, columns, and structure of each dataset
           - You may select multiple datasets if the query spans multiple datasets
           - If no dataset is suitable, provide clear reasoning why

        3. For each selected dataset, identify:
           - The specific columns that will be needed for the analysis
           - Expected values or value ranges that might be relevant to the query
           - Any potential filters or conditions that would be applied

        RESPONSE FORMAT:
        Respond in this JSON format:
        {{
            "selected_dataset": ["dataset_name1", "dataset_name2"],
            "reasoning": "Clear explanation of why these datasets were selected",
            "column_requirements": [
                {{
                    "dataset": "dataset_name1",
                    "columns": [
                        {{
                            "name": "column_name",
                            "expected_values": ["value1", "value2"] or "range: min-max",
                            "filter_condition": "equals/greater than/less than/between/etc"
                        }}
                    ]
                }}
            ]
        }}
    """

def identify_datasets(state: State):
    """
    Identify relevant dataset based on natural language query.
    Since we already know this is a data query, we directly identify the datasets
    without making tool calls.
    """
    parser = JsonOutputParser()
    query_index = state.get("subquery_index", 0)
    user_query = state.get("subqueries")[query_index] if state.get("subqueries") else 'No input'
    query_result = state.get("query_result", {})

    datasets_info = []

    for file in os.listdir("./data"):
        if file.endswith(".csv"):
            info = get_dataset_preview(file)
            datasets_info.append(info)

    try:
        prompt = create_llm_prompt(user_query, datasets_info)
        response: Any = lc.llm.invoke(prompt)

        response_content = str(response.content)
        parsed_content = parser.parse(response_content)

        selected_datasets = parsed_content.get("selected_dataset", [])
        query_result.subqueries[query_index].tables_used = selected_datasets

        return {
            "query_result": query_result,
            "datasets": selected_datasets,
            "messages": [IntermediateStep.from_text(json.dumps(parsed_content, indent=2))],
        }

    except Exception as e:
        error_msg = f"Error identifying datasets: {str(e)}"
        query_result.add_error_message(str(e), "Error identifying datasets")
        return {
            "query_result": query_result,
            "datasets": None,
            "messages": [ErrorMessage.from_text(json.dumps({"error": error_msg}, indent=2))]
        }