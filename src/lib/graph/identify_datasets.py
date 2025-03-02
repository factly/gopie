from lib.graph.types import IntermediateStep, ErrorMessage, State
import pandas as pd
from typing import Dict, Any, List, Optional
import os
import json
from lib.langchain_config import lc
from langchain_core.output_parsers import JsonOutputParser
from rich.console import Console
console = Console()

def get_dataset_metadata(selected_datasets: Optional[List[str]]) -> Dict[str, Any]:
    """Get metadata for all available datasets"""
    datasets = {}
    data_dir = "./data"

    for file in os.listdir(data_dir):
        if file.endswith('.csv'):
            if selected_datasets and file not in selected_datasets:
                continue
            try:
                df = pd.read_csv(os.path.join(data_dir, file))
                datasets[file] = {
                    "name": file,
                    "columns": list(df.columns),
                    "rows": len(df),
                    "description": f"Dataset containing {len(df)} records with columns: {', '.join(df.columns[:5])}..."
                }
            except Exception:
                continue

    return datasets

def create_llm_prompt(user_query: str, datasets_metadata: Dict[str, Any]) -> str:
    """Create a prompt for the LLM to identify the relevant dataset"""
    return f"""
        Given the following user query and available datasets, analyze whether the query is requesting data analysis from the available datasets.

        User Query: "{user_query}"

        Available Datasets:
        {json.dumps(datasets_metadata, indent=2)}

        IMPORTANT: Only identify a dataset if the user is clearly asking for data analysis related to the available datasets.
        If the user is just greeting, chatting, asking general questions not related to data analysis, or their query cannot be answered with these datasets, DO NOT select any dataset.

        Analyze the query and respond in JSON format:
        {{
            "selected_dataset": "name of the most relevant dataset with the exact name provided in the metadata without the extension, or empty string if no dataset is relevant",
            "reasoning": "brief explanation of why this dataset is relevant or why no dataset was selected",
            "is_data_query": true/false (whether this is a data-related query or just conversation)
        }}
    """

def identify_datasets(state: State):
    """
    Use LLM to identify relevant dataset based on natural language query.
    """
    parser = JsonOutputParser()
    user_input = state['messages'][0].content if state['messages'] else ''

    try:
        if not user_input:
            error_data = {
                "error": "No user query provided",
                "is_data_query": False
            }
            return {
                "datasets": None,
                "user_query": user_input,
                "conversational": False,
                "messages": [ErrorMessage.from_text(json.dumps(error_data, indent=2))],
            }

        datasets_metadata = get_dataset_metadata(None)
        llm_prompt = create_llm_prompt(user_input, datasets_metadata)

        response = lc.llm.invoke(llm_prompt)
        response_content = str(response.content)

        # Ensure we always return the raw JSON string for consistency
        return {
            "datasets": datasets_metadata,
            "user_query": user_input,
            "conversational": not parser.parse(response_content).get("is_data_query", False),
            "messages": [IntermediateStep.from_text(response_content)],
        }

    except Exception as e:
        error_msg = f"Error identifying datasets: {str(e)}"
        return {
            "datasets": None,
            "user_query": user_input,
            "conversational": False,
            "messages": [ErrorMessage.from_text(json.dumps({"error": error_msg}, indent=2))]
        }

def is_conversational_input(state: State) -> str:
    """
    If no dataset was selected, generate a response.
    If a dataset was selected, plan the query execution.
    """
    parser = JsonOutputParser()

    try:
        response_content = state["messages"][-1].content
        parsed_response = parser.parse(response_content)

        is_data_query = parsed_response.get("is_data_query", False)
        has_dataset = "selected_dataset" in parsed_response and parsed_response["selected_dataset"]

        if is_data_query and has_dataset:
            return "plan_query"
        else:
            return "generate_response"
    except Exception as e:
        error_data = {
            "error": f"Error determining input type: {str(e)}",
            "is_data_query": False,
            "selected_dataset": "",
            "reasoning": "Failed to parse the previous response"
        }

        state["messages"][-1] = ErrorMessage.from_text(json.dumps(error_data, indent=2))
        return "generate_response"