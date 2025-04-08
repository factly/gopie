import json
import logging
from typing import Any, List

from app.core.langchain_config import lc
from app.models.message import ErrorMessage, IntermediateStep
from app.models.schema import DatasetSchema
from app.services.qdrant.dataset_search import search_schemas
from app.workflow.graph.types import State
from langchain_core.output_parsers import JsonOutputParser


def create_llm_prompt(
    user_query: str, available_datasets_schemas: List[DatasetSchema]
) -> str:
    """Create a prompt for the LLM to identify the relevant dataset and required columns"""
    return f"""
        You are an AI assistant specialized in data analysis. Your role is to help users analyze data by identifying relevant datasets and column values.

        USER QUERY:
        "{user_query}"

        PRE-FILTERED DATASETS SCHEMAS (ordered by relevance):
        {json.dumps(available_datasets_schemas, indent=2)}

        INSTRUCTIONS:
        1. The datasets above have been pre-filtered using semantic search based on relevance to the user query.

        2. Based on the user query, confirm which of these pre-filtered datasets best matches the user's needs.
           - Consider the content, columns, and structure of each dataset
           - The datasets are already ranked by relevance, but you should still critically evaluate them
           - You may select multiple datasets if the query spans multiple datasets
           - You can override the vector search ranking if you have strong reasons
           - If no dataset is suitable, provide clear reasoning why

        3. For each selected dataset, identify:
           - The specific columns that will be needed for the analysis
           - For string columns in datasets list the specific string column values that might be relevant to the query
           - Don't include the column names that are numeric type

        RESPONSE FORMAT:
        Respond in this JSON format:
        {{
            "selected_dataset": ["dataset_name1", "dataset_name2"],
            "reasoning": "Clear explanation of why these datasets were selected",
            "column_predicted": [
                {{
                    "dataset": "dataset_name1",
                    "columns": [
                        {{
                            "name": "column_name",
                            "expected_values": ["value1", "value2", "value3"] // Include if the column contains string values
                        }}
                    ]
                }}
            ]
        }}
    """


async def identify_datasets(state: State):
    """
    Identify relevant dataset based on natural language query.
    Uses Qdrant vector search to find the most relevant datasets first.
    """
    parser = JsonOutputParser()
    query_index = state.get("subquery_index", 0)
    user_query = (
        state.get("subqueries")[query_index] if state.get("subqueries") else "No input"
    )
    query_result = state.get("query_result", {})
    dataset_ids = state.get("dataset_ids", [])
    project_ids = state.get("project_ids", [])

    try:
        datasets_info = []
        try:
            dataset_schemas = search_schemas(
                user_query, dataset_ids=dataset_ids, project_ids=project_ids
            )
            datasets_info = dataset_schemas

        except Exception as e:
            logging.warning(
                f"Vector search error: {str(e)}. Unable to retrieve dataset information."
            )

        if not datasets_info:
            return {
                "query_result": query_result,
                "datasets": None,
                "messages": [
                    ErrorMessage.from_text(
                        json.dumps({"error": "No relevant datasets found"}, indent=2)
                    )
                ],
            }

        prompt = create_llm_prompt(user_query, datasets_info)
        response: Any = await lc.llm.ainvoke(prompt)

        response_content = str(response.content)
        parsed_content = parser.parse(response_content)

        selected_datasets = parsed_content.get("selected_dataset", [])
        query_result.subqueries[query_index].tables_used = selected_datasets
        column_assumptions = parsed_content.get("column_predicted", [])

        dataset_info = {
            "column_assumptions": column_assumptions,
            "schema": datasets_info,
        }

        return {
            "query_result": query_result,
            "dataset_info": dataset_info,
            "datasets": selected_datasets,
            "messages": [
                IntermediateStep.from_text(json.dumps(parsed_content, indent=2))
            ],
        }

    except Exception as e:
        error_msg = f"Error identifying datasets: {str(e)}"
        query_result.add_error_message(str(e), "Error identifying datasets")
        return {
            "query_result": query_result,
            "datasets": None,
            "messages": [
                ErrorMessage.from_text(json.dumps({"error": error_msg}, indent=2))
            ],
        }
