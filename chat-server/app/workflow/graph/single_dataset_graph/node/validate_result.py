from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnableConfig

from app.core.config import settings
from app.models.message import AIMessage, ErrorMessage
from app.utils.langsmith.prompt_manager import get_prompt
from app.utils.model_registry.model_provider import get_model_provider
from app.workflow.events.event_utils import configure_node
from app.workflow.graph.single_dataset_graph.types import State

RECOMMENDATION_LIST = ["pass_on_results", "rerun_query"]


@configure_node(
    role="intermediate",
    progress_message="Validating query result...",
)
async def validate_result(state: State, config: RunnableConfig) -> dict:
    """
    Validate the query result using a language model and return the validation outcome, updated retry count, and workflow messages.

    If the language model's recommendation is "rerun_query", the retry count is incremented.
    If the recommendation is not recognized, an error is raised and an error message is returned in the messages list.
    On successful validation, returns the parsed validation result and an intermediate step message;
    on failure, returns `None` for the validation result and an error message.

    Returns:
        dict: A dictionary containing the updated `retry_count`, the `validation_result` (or `None` on error), and a list of workflow messages.
    """
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

        recommendation = parsed_response["recommendation"]
        response = parsed_response["response"]

        if recommendation not in RECOMMENDATION_LIST:
            raise ValueError(f"Invalid recommendation: {recommendation}")

        if recommendation == "rerun_query":
            retry_count += 1

        return {
            "retry_count": retry_count,
            "messages": [AIMessage(content=response)],
            "recommendation": recommendation,
            "response": response,
        }

    except Exception as e:
        return {
            "retry_count": retry_count,
            "messages": [
                ErrorMessage(content=f"Validation error: {str(e)}. Proceeding with response.")
            ],
        }


async def route_result_validation(state: State) -> str:
    """
    Determine the next workflow action based on the validation result, retry count, and last message.

    Returns:
        str: The recommended action, either "pass_on_results" or "rerun_query", based on validation outcome and workflow state.
    """
    recommendation = state.get("recommendation", "pass_on_results")
    retry_count = state.get("retry_count", 0)
    last_message = state.get("messages", [])[-1]

    if (
        recommendation == "pass_on_results"
        or retry_count >= settings.MAX_VALIDATION_RETRY_COUNT
        or isinstance(last_message, ErrorMessage)
    ):
        return "pass_on_results"

    if recommendation in RECOMMENDATION_LIST:
        return recommendation

    return "pass_on_results"
