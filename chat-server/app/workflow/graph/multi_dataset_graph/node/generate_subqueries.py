from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from app.core.log import custom_logger as logger
from app.models.message import ErrorMessage, IntermediateStep
from app.models.schema import DatasetSchema
from app.services.qdrant.get_schema import get_project_schemas
from app.utils.langsmith.prompt_manager import get_prompt_llm_chain
from app.workflow.events.event_utils import (
    configure_node,
    fake_streaming_response,
)
from app.workflow.graph.multi_dataset_graph.types import State


async def _format_context_info(
    project_ids: list[str] | None,
    max_datasets: int = 30,
) -> str:
    """
    Fetch and format project context and available datasets information from Qdrant.

    Args:
        project_ids: List of project IDs (or None)
        max_datasets: Maximum number of datasets to include in the context

    Returns:
        Formatted string containing project context and available datasets
    """
    if not project_ids:
        return ""

    context_info = ""

    try:
        dataset_schemas: list[DatasetSchema] = await get_project_schemas(project_ids[0], limit=50)

        if not dataset_schemas:
            return ""

        project_custom_prompt = dataset_schemas[0].project_custom_prompt

        context_info = "PROJECT CONTEXT:\n"
        if project_custom_prompt:
            context_info += f"Custom Instructions: {project_custom_prompt}\n"

        context_info += "\nAVAILABLE DATASETS:\n"
        for ds in dataset_schemas[:max_datasets]:
            context_info += f"  - {ds.name}"
            if ds.dataset_name and ds.dataset_name != ds.name:
                context_info += f" (Table: {ds.dataset_name})"
            if ds.dataset_description:
                desc = ds.dataset_description[:100]
                context_info += f": {desc}..."
            context_info += "\n"
    except Exception as e:
        logger.warning(f"Could not fetch project context: {e}. Proceeding without context.")

    return context_info


class GenerateSubqueriesOutput(BaseModel):
    needs_breakdown: bool = Field(
        description="Whether the query needs to be broken down into subqueries"
    )
    explanation: str = Field(description="Brief explanation of the decision about query complexity")
    subqueries: list[str] = Field(
        description="List of generated subqueries in natural language. Empty if needs_breakdown is false, exactly 2 if needs_breakdown is true",
        default=[],
    )
    status_message: str = Field(
        description="Status message about the progress. If breakdown needed, include the subqueries. Otherwise, explain why no breakdown is needed."
    )


@configure_node(
    role="intermediate",
    progress_message="Checking query complexity...",
)
async def generate_subqueries(state: State, config: RunnableConfig):
    user_input = state.get("user_query", "")
    query_result = state.get("query_result")
    project_ids = state.get("project_ids", [])

    context_info = await _format_context_info(project_ids)

    try:
        subqueries_llm = get_prompt_llm_chain(
            "generate_subqueries", config, schema=GenerateSubqueriesOutput
        )
        response = await subqueries_llm.ainvoke(
            {
                "user_input": user_input,
                "context_info": context_info,
            }
        )

        needs_breakdown = response.needs_breakdown
        explanation = response.explanation
        status_message = response.status_message

        if status_message:
            await fake_streaming_response(status_message, config)

        if needs_breakdown:
            subqueries = response.subqueries
            if len(subqueries) > 2:
                subqueries = subqueries[:2]
            if not subqueries or len(subqueries) < 2:
                subqueries = [user_input]
        else:
            subqueries = [user_input]

        for subquery_text in subqueries:
            query_result.add_subquery(
                query_text=subquery_text,
                sql_queries=[],
                tables_used=None,
            )

        return {
            "user_query": user_input,
            "subquery_index": 0,
            "subqueries": subqueries,
            "query_result": query_result,
            "messages": [
                IntermediateStep.from_json(
                    {
                        "needs_breakdown": needs_breakdown,
                        "subqueries": subqueries,
                        "original_query": user_input,
                        "explanation": explanation,
                    },
                )
            ],
        }
    except Exception as e:
        error_msg = f"Error in subquery generation: {e!s}"
        default_subqueries = [user_input]

        query_result.add_subquery(
            query_text=user_input,
            sql_queries=[],
            tables_used=None,
        )

        logger.exception(error_msg)

        return {
            "user_query": user_input,
            "subquery_index": 0,
            "subqueries": default_subqueries,
            "query_result": query_result,
            "messages": [ErrorMessage(content=error_msg)],
        }
