from typing import Any

from langchain_core.messages import AIMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.runnables import RunnableConfig

from app.core.config import settings
from app.models.message import ErrorMessage
from app.utils.langsmith.prompt_manager import get_prompt
from app.utils.model_registry.model_provider import get_model_provider
from app.workflow.events.event_utils import configure_node
from app.workflow.graph.multi_dataset_graph.types import State

RECOMMENDATION_LIST = ["route_response", "replan", "reidentify_datasets"]


@configure_node(
    role="intermediate",
    progress_message="Validating query result...",
)
async def validate_result(state: State, config: RunnableConfig) -> dict[str, Any]:
    """
    Validates the query result using a language model and updates the workflow state with the validation outcome.

    The function sends the previous query result to a language model for validation, parses the response, and checks
    that the recommendation is valid. If the recommendation is to reidentify datasets or replan, the retry count is incremented.
    Returns an updated state dictionary with the retry count, validation result, and an intermediate step message.
    If validation fails, returns the current retry count, a null validation result, and an error message.

    Returns:
        dict: Updated workflow state containing the retry count, validation result (or None on error), and a list of messages reflecting the validation outcome.
    """
    query_result = state["query_result"]
    retry_count = state.get("retry_count", 0)
    subquery_index = state.get("subquery_index", 0)

    no_sql_response = query_result.subqueries[subquery_index].no_sql_response

    if no_sql_response:
        return {
            "retry_count": retry_count,
            "messages": [
                AIMessage(
                    content=f"No SQL response for subquery {subquery_index + 1}. Proceeding further."
                )
            ],
            "recommendation": "route_response",
        }

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

        if recommendation == "reidentify_datasets" or recommendation == "replan":
            retry_count += 1

        return {
            "retry_count": retry_count,
            "messages": [AIMessage(content=response)],
            "recommendation": recommendation,
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
    Determine the next workflow routing step based on the validation result, retry count, and last message in the state.

    Returns:
        str: The routing decision, which is either a recommendation from the validation result or "route_response"
        if validation is valid, retry limit is reached, an error occurred, or no valid recommendation is present.
    """
    last_message = state.get("messages", [])[-1]
    retry_count = state.get("retry_count", 0)
    recommendation = state.get("recommendation", "route_response")

    if retry_count >= settings.MAX_VALIDATION_RETRY_COUNT or isinstance(last_message, ErrorMessage):
        return "route_response"

    if recommendation in RECOMMENDATION_LIST:
        return recommendation

    return "route_response"
