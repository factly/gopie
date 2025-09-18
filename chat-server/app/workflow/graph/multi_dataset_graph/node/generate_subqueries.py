from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from app.core.log import custom_logger as logger
from app.models.message import ErrorMessage, IntermediateStep
from app.utils.langsmith.prompt_manager import get_prompt_llm_chain
from app.workflow.events.event_utils import (
    configure_node,
    fake_streaming_response,
)
from app.workflow.graph.multi_dataset_graph.types import State


class AssessQueryComplexityOutput(BaseModel):
    needs_breakdown: bool = Field(
        description="Whether the query needs to be broken down into subqueries"
    )
    explanation: str = Field(description="Brief explanation of the decision about query complexity")
    status_message: str = Field(
        description="Status message about the progress of the generate_subqueries node"
    )


class GenerateSubqueriesOutput(BaseModel):
    subqueries: list[str] = Field(
        description="List of generated subqueries in natural language", min_length=2, max_length=2
    )
    status_message: str = Field(
        description="Status message about the progress of the generate_subqueries node. Please include the subqueries that are generated in the status message."
    )


@configure_node(
    role="intermediate",
    progress_message="Checking query complexity...",
)
async def generate_subqueries(state: State, config: RunnableConfig):
    user_input = state.get("user_query", "")
    query_result = state.get("query_result")

    try:
        assessment_llm = get_prompt_llm_chain(
            "assess_query_complexity", config, schema=AssessQueryComplexityOutput
        )
        assessment_response = await assessment_llm.ainvoke({"user_input": user_input})

        needs_breakdown = assessment_response.needs_breakdown
        explanation = assessment_response.explanation

        subqueries = []

        if needs_breakdown:
            subqueries_llm = get_prompt_llm_chain(
                "generate_subqueries", config, schema=GenerateSubqueriesOutput
            )
            subqueries_response = await subqueries_llm.ainvoke({"user_input": user_input})

            subqueries = subqueries_response.subqueries
            status_message = subqueries_response.status_message

            if status_message:
                await fake_streaming_response(status_message, config)

            if len(subqueries) > 2:
                subqueries = subqueries[:2]

            if not subqueries:
                subqueries = [user_input]
        else:
            status_message = assessment_response.status_message
            if status_message:
                await fake_streaming_response(status_message, config)

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
