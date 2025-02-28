from lib.graph.types import IntermediateStep, State
import pandas as pd
from typing import Dict, Any, List, Optional
import os
import json
from lib.langchain_config import lc
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
        Given the following user query and available datasets, identify the most relevant dataset to answer the query. Dont modify the dataset name.

        User Query: "{user_query}"

        Available Datasets:
        {json.dumps(datasets_metadata, indent=2)}

        Analyze the query and respond in JSON format:
        {{
            "selected_dataset": "name of the most relevant dataset with the exact name provided in the metadata without the extension",
            "reasoning": "brief explanation of why this dataset is relevant",
            "query_intent": "what the user is trying to do with the data"
        }}
    """

def identify_datasets(state: State):
    """
    Use LLM to identify relevant dataset based on natural language query.
    """
    try:
        user_input = state['messages'][0].content if state['messages'] else ''
        if not user_input:
            raise ValueError("No user query provided")

        datasets_metadata = get_dataset_metadata(None)
        llm_prompt = create_llm_prompt(user_input, datasets_metadata)

        response = lc.llm.invoke(llm_prompt)

        return {
            "datasets": datasets_metadata,
            "user_query": user_input,
            "messages": [IntermediateStep.from_text(str(response.content))],
        }

    except Exception as e:
        error_message = f"Error processing query: {str(e)}"
        return {
            "datasets": None,
            "user_query": user_input,
            "messages": [IntermediateStep.from_text(error_message)],
        }