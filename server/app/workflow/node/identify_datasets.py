import logging
from typing import Any

from langchain_core.callbacks.manager import adispatch_custom_event
from langchain_core.output_parsers import JsonOutputParser

from app.core.langchain_config import (
    get_embeddings_model_with_trace,
    get_llm_with_trace,
)
from app.models.message import ErrorMessage, IntermediateStep
from app.services.qdrant.schema_search import search_schemas
from app.workflow.graph.types import State
from app.workflow.prompts.prompt_selector import get_prompt


async def identify_datasets(state: State):
    """
    Identify relevant dataset based on natural language query.
    Uses Qdrant vector search to find the most relevant datasets first.
    """
    parser = JsonOutputParser()
    query_index = state.get("subquery_index", 0)
    user_query = (
        state.get("subqueries")[query_index]
        if state.get("subqueries")
        else "No input"
    )
    query_result = state.get("query_result", {})
    dataset_ids = state.get("dataset_ids", [])
    project_ids = state.get("project_ids", [])

    try:
        llm = get_llm_with_trace(state.get("trace_id"))
        embeddings_model = get_embeddings_model_with_trace(
            state.get("trace_id")
        )

        semantic_searched_datasets = []
        try:
            dataset_schemas = await search_schemas(
                user_query,
                embeddings_model,
                dataset_ids=dataset_ids,
                project_ids=project_ids,
            )
            semantic_searched_datasets = dataset_schemas

        except Exception as e:
            logging.warning(
                f"Vector search error: {e!s}. Unable to retrieve dataset "
                "information."
            )

        if not semantic_searched_datasets:
            await adispatch_custom_event(
                "datasets_identified",
                {
                    "content": "No relevant datasets found",
                    "datasets": None,
                },
            )

            return {
                "query_result": query_result,
                "datasets": None,
                "messages": [
                    ErrorMessage.from_json(
                        {"error": "No relevant datasets found"}
                    )
                ],
            }

        llm_prompt = get_prompt(
            "identify_datasets",
            user_query=user_query,
            available_datasets_schemas=semantic_searched_datasets,
        )

        llm = get_llm_with_trace(state.get("trace_id"))
        response: Any = await llm.ainvoke({"input": llm_prompt})

        response_content = str(response.content)
        parsed_content = parser.parse(response_content)

        selected_datasets = parsed_content.get("selected_dataset", [])
        query_result.subqueries[query_index].tables_used = selected_datasets
        column_assumptions = parsed_content.get("column_predicted", [])

        filtered_dataset_schemas = [
            schema
            for schema in semantic_searched_datasets
            if schema.get("name") in selected_datasets
        ]

        dataset_name_mapping = {}
        for schema in filtered_dataset_schemas:
            dataset_name_mapping[schema.get("name")] = schema.get(
                "dataset_name", schema.get("name")
            )

        datasets_info = {
            "column_assumptions": column_assumptions,
            "schemas": filtered_dataset_schemas,
            "dataset_name_mapping": dataset_name_mapping,
        }

        await adispatch_custom_event(
            "dataful-agent",
            {
                "content": "Datasets identified",
                "datasets": selected_datasets,
            },
        )

        return {
            "query_result": query_result,
            "datasets_info": datasets_info,
            "datasets": selected_datasets,
            "messages": [IntermediateStep.from_json(parsed_content)],
        }

    except Exception as e:
        error_msg = f"Error identifying datasets: {e!s}"
        query_result.add_error_message(str(e), "Error identifying datasets")

        await adispatch_custom_event(
            "dataful-agent",
            {
                "content": "Error identifying datasets",
                "datasets": None,
            },
        )

        return {
            "query_result": query_result,
            "datasets": None,
            "messages": [ErrorMessage.from_json({"error": error_msg})],
        }
