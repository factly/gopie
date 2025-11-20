from langchain_core.callbacks import adispatch_custom_event
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from app.core.log import custom_logger as logger
from app.models.message import ErrorMessage, IntermediateStep
from app.utils.graph_utils.column_value_matching import match_column_values
from app.utils.graph_utils.validate_match_relevance import (
    validate_match_relevance,
)
from app.utils.langsmith.prompt_manager import get_prompt_llm_chain
from app.workflow.events.event_utils import configure_node
from app.workflow.graph.multi_dataset_graph.types import (
    ColumnAssumptions,
    State,
)


class RegenerateFuzzyValuesOutput(BaseModel):
    column_assumptions: list[ColumnAssumptions] = Field(
        description="Updated column assumptions with new fuzzy values for failed searches"
    )
    reasoning: str = Field(
        description="Explanation of why these alternative fuzzy values were chosen"
    )
    status_message: str = Field(
        description="A short 1 line message for describing the outcome of the fuzzy value regeneration without technical jargon"
    )


@configure_node(
    role="intermediate",
    progress_message="Analyzing dataset structure and validating column values...",
)
async def analyze_dataset(state: State, config: RunnableConfig) -> dict:
    """
    Analyze dataset structure and validate fuzzy matches.

    - Matches column values against database
    - Validates Levenshtein matches with LLM for relevance
    - Retries with regenerated fuzzy values (up to 3 times) if matches fail
    """
    query_result = state["query_result"]
    datasets_info = state["datasets_info"]
    last_message = state.get("messages", [])[-1]
    retry_count = state.get("analyze_dataset_retry_count", 0)
    subqueries = state.get("subqueries", [])
    subquery_index = state.get("subquery_index", 0)
    current_query = subqueries[subquery_index]

    try:
        if isinstance(last_message, ErrorMessage):
            return {}

        column_assumptions = datasets_info.get("column_assumptions", [])
        if not column_assumptions:
            raise ValueError("No column assumptions found in the datasets_info.")

        column_mappings = await match_column_values(column_assumptions=column_assumptions)

        logger.debug("Validating fuzzy match relevance with LLM...")
        column_mappings = await validate_match_relevance(
            analyze_dataset_result=column_mappings,
            user_query=state["user_query"],
            config=config,
        )

        failed_fuzzy_searches = _collect_failed_searches(column_mappings)
        has_failures = bool(failed_fuzzy_searches)

        if has_failures and retry_count < 3:
            logger.info(
                f"Fuzzy value search failures detected. Retry attempt {retry_count + 1}/3. "
                f"Failed searches: {failed_fuzzy_searches}"
            )

            try:
                response = await _regenerate_fuzzy_values(
                    current_query=current_query,
                    datasets_info=datasets_info,
                    failed_fuzzy_searches=failed_fuzzy_searches,
                    retry_count=retry_count,
                    config=config,
                )

                # Merge regenerated assumptions with existing ones, preserving validated columns
                merged_assumptions = _merge_column_assumptions(
                    existing_assumptions=column_assumptions,
                    regenerated_assumptions=response.column_assumptions,
                    failed_searches=failed_fuzzy_searches,
                )

                datasets_info["column_assumptions"] = merged_assumptions
                datasets_info["correct_column_requirements"] = None

                return {
                    "datasets_info": datasets_info,
                    "analyze_dataset_retry_count": retry_count + 1,
                    "messages": [
                        IntermediateStep(
                            content=f"Retrying with alternative search terms: {response.reasoning}"
                        )
                    ],
                }

            except Exception as e:
                logger.exception(f"Error regenerating fuzzy values: {e!s}")

        # Only log the final state if there are failures even after retries
        if has_failures:
            if retry_count >= 3:
                logger.warning(
                    f"Maximum retry attempts (3) reached. Moving forward with available results. "
                    f"Remaining failed searches: {failed_fuzzy_searches}"
                )

        datasets_info["correct_column_requirements"] = column_mappings
        datasets_info["column_assumptions"] = None

        return {
            "datasets_info": datasets_info,
            "analyze_dataset_retry_count": 0,
            "messages": [
                IntermediateStep(
                    content=f"Analyzed values for {len(column_mappings.datasets)} datasets"
                )
            ],
        }

    except Exception as e:
        error_msg = f"Error analyzing dataset: {e!s}"
        query_result.add_error_message(error_msg, "Error analyzing dataset")
        logger.exception(error_msg)

        return {
            "query_result": query_result,
            "analyze_dataset_retry_count": 0,
            "messages": [ErrorMessage(content=error_msg)],
        }


def _merge_column_assumptions(
    existing_assumptions: list[ColumnAssumptions],
    regenerated_assumptions: list[ColumnAssumptions],
    failed_searches: dict,
) -> list[ColumnAssumptions]:
    """
    Merge regenerated column assumptions with existing ones.
    Only updates fuzzy values for columns that failed validation.
    Preserves all other column assumptions that passed validation.
    """
    # Create a lookup for regenerated assumptions by dataset and column
    regenerated_lookup = {}
    for dataset_assumption in regenerated_assumptions:
        dataset_name = dataset_assumption["dataset"]
        regenerated_lookup[dataset_name] = {}
        for column in dataset_assumption["columns"]:
            regenerated_lookup[dataset_name][column["name"]] = column

    # Merge assumptions
    merged_assumptions = []
    for dataset_assumption in existing_assumptions:
        dataset_name = dataset_assumption["dataset"]
        merged_columns = []

        for column in dataset_assumption["columns"]:
            column_name = column["name"]

            # Check if this column had failed searches
            has_failed_searches = (
                dataset_name in failed_searches and column_name in failed_searches[dataset_name]
            )

            # If column failed and we have a regenerated version, use it
            if (
                has_failed_searches
                and dataset_name in regenerated_lookup
                and column_name in regenerated_lookup[dataset_name]
            ):
                merged_columns.append(regenerated_lookup[dataset_name][column_name])
            else:
                # Keep the existing column assumption (it passed validation)
                merged_columns.append(column)

        merged_assumptions.append({"dataset": dataset_name, "columns": merged_columns})

    return merged_assumptions


def _collect_failed_searches(column_mappings) -> dict:
    """Collect failed fuzzy searches with error details for regeneration."""
    failed_fuzzy_searches = {}

    for dataset_name, dataset_analysis in column_mappings.datasets.items():
        for column_analysis in dataset_analysis.columns_analyzed:
            failed_items = []

            for suggestion in column_analysis.suggested_alternatives:
                is_failed = (
                    not suggestion.found_similar_values
                    or suggestion.match_source in ["validation_failed", "sql_error"]
                    or (
                        suggestion.match_source == "levenshtein" and suggestion.is_relevant is False
                    )
                )

                if is_failed:
                    item = {"value": suggestion.requested_value}
                    if suggestion.error_message:
                        item["error"] = suggestion.error_message
                    failed_items.append(item)

                    if suggestion.is_relevant is False:
                        logger.info(
                            f"Levenshtein match rejected: '{suggestion.requested_value}' "
                            f"(relevance: {suggestion.relevance_score:.0f}%)"
                        )

            if failed_items:
                if dataset_name not in failed_fuzzy_searches:
                    failed_fuzzy_searches[dataset_name] = {}
                failed_fuzzy_searches[dataset_name][column_analysis.column_name] = failed_items

    return failed_fuzzy_searches


async def _regenerate_fuzzy_values(
    current_query: str,
    datasets_info,
    failed_fuzzy_searches: dict,
    retry_count: int,
    config: RunnableConfig,
) -> RegenerateFuzzyValuesOutput:
    """
    Regenerate fuzzy values using LLM for failed searches.
    """

    dataset_schemas = datasets_info.get("schemas", [])

    chain_input = {
        "user_query": current_query,
        "dataset_schemas": dataset_schemas,
        "failed_fuzzy_searches": failed_fuzzy_searches,
        "retry_attempt": retry_count + 1,
    }

    chain = get_prompt_llm_chain(
        "regenerate_fuzzy_values",
        config,
        schema=RegenerateFuzzyValuesOutput,
    )
    response = await chain.ainvoke(chain_input)

    await adispatch_custom_event(
        "gopie-agent",
        {"content": response.status_message or ""},
    )

    return response


def route_from_analyze_dataset(state: State) -> str:
    datasets_info = state.get("datasets_info", {})
    retry_count = state.get("analyze_dataset_retry_count", 0)

    column_assumptions = datasets_info.get("column_assumptions")

    if column_assumptions and retry_count > 0 and retry_count < 3:
        logger.info(f"Routing back to analyze_dataset for retry {retry_count}")
        return "analyze_dataset"

    return "plan_query"
