from typing import Any

from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnableConfig

from app.core.config import settings
from app.models.message import ErrorMessage, IntermediateStep
from app.utils.langsmith.prompt_manager import get_prompt
from app.utils.model_registry.model_provider import get_model_provider
from app.workflow.events.event_utils import configure_node
from app.workflow.graph.single_dataset_graph.types import State
from app.models.query import ValidationResult


RECOMMENDATION_LIST = ["pass_on_results", "rerun_query"]


@configure_node(
    role="intermediate",
    progress_message="Validating query result...",
)
async def validate_result(state: State, config: RunnableConfig) -> dict[str, Any]:
    query_result = state.get("query_result", None)
    retry_count = state.get("retry_count", 0)

    # Validate the result with the LLM
    try:
        prompt_messages = get_prompt(
            "validate_result",
            prev_query_result=query_result,
        )

        llm = get_model_provider(config).get_llm_for_node("validate_result")
        parser = JsonOutputParser()
        response = await llm.ainvoke(prompt_messages)
        parsed_response = parser.parse(str(response.content))
        validation_result = ValidationResult(**parsed_response)

        if validation_result["recommendation"] not in RECOMMENDATION_LIST:
            raise ValueError(f"Invalid recommendation: {validation_result['recommendation']}")

        if validation_result["recommendation"] == "rerun_query":
            retry_count += 1

        return {
            "retry_count": retry_count,
            "validation_result": validation_result,
            "messages": [IntermediateStep.from_json(parsed_response)],
        }

    except Exception as e:
        return {
            "retry_count": retry_count,
            "validation_result": None,
            "messages": [
                ErrorMessage(content=f"Validation error: {str(e)}. Proceeding with response.")
            ],
        }


async def route_result_validation(state: State) -> str:
    last_message = state.get("messages", [])[-1]
    validation_result = state.get("validation_result", None)
    retry_count = state.get("retry_count", 0)

    if not validation_result:
        return "pass_on_results"

    is_valid = validation_result["is_valid"]
    recommendation = validation_result["recommendation"]

    if (
        is_valid
        or retry_count >= settings.MAX_VALIDATION_RETRY_COUNT
        or isinstance(last_message, ErrorMessage)
    ):
        return "pass_on_results"

    if recommendation in RECOMMENDATION_LIST:
        return recommendation

    return "pass_on_results"
