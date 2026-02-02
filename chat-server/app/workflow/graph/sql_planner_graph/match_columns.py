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
from app.workflow.graph.sql_planner_graph.types import ColumnAssumptions, State


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
async def match_columns(state: State, config: RunnableConfig) -> dict:
    """
    Analyze dataset structure and validate fuzzy matches.

    - Matches column values against database
    - Validates Levenshtein matches with LLM for relevance
    - Retries with regenerated fuzzy values (up to 3 times) if matches fail

    Supports both multi-dataset and single-dataset workflows.
    """
    # Determine which dataset info to use
    multi_datasets_info = state.get("multi_datasets_info")
    single_dataset_info = state.get("single_dataset_info")

    # Use whichever is available
    datasets_info = multi_datasets_info or single_dataset_info
    is_single_dataset = single_dataset_info is not None and multi_datasets_info is None

    if not datasets_info:
        return {}

    user_query = state.get("user_query", "")
    messages = state.get("messages", [])
    last_message = messages[-1] if messages else None
    retry_count = state.get("match_columns_retry_count", 0)

    # subqueries not present in SQL Planner State, using user_query directly
    current_query = user_query

    try:
        if isinstance(last_message, ErrorMessage):
            return {}

        column_assumptions = datasets_info.get("column_assumptions", [])
        if not column_assumptions:
            # It's possible there are no assumptions to verify, so we just proceed
            return {}

        org_id = config.get("metadata", {}).get("org_id", None)
        column_mappings = await match_column_values(
            column_assumptions=column_assumptions, org_id=org_id
        )

        column_mappings = await validate_match_relevance(
            analyze_dataset_result=column_mappings,
            user_query=user_query,
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

                merged_assumptions = _merge_column_assumptions(
                    existing_assumptions=column_assumptions,
                    regenerated_assumptions=response.column_assumptions,
                    failed_searches=failed_fuzzy_searches,
                )

                datasets_info["column_assumptions"] = merged_assumptions
                datasets_info["correct_column_requirements"] = None

                result = {
                    "match_columns_retry_count": retry_count + 1,
                    "messages": [
                        IntermediateStep(
                            content=f"Retrying with alternative search terms: {response.reasoning}"
                        )
                    ],
                }

                # Return the updated info in the correct state key
                if is_single_dataset:
                    result["single_dataset_info"] = datasets_info
                else:
                    result["multi_datasets_info"] = datasets_info

                return result

            except Exception as e:
                logger.exception(f"Error regenerating fuzzy values: {e!s}")

        if has_failures:
            if retry_count >= 3:
                logger.warning(
                    f"Maximum retry attempts (3) reached. Moving forward with available results. "
                    f"Remaining failed searches: {failed_fuzzy_searches}"
                )

        datasets_info["correct_column_requirements"] = column_mappings
        datasets_info["column_assumptions"] = None

        result = {
            "match_columns_retry_count": 0,
            "messages": [
                IntermediateStep(
                    content=f"Analyzed values for {len(column_mappings.datasets)} datasets"
                )
            ],
        }

        # Return the updated info in the correct state key
        if is_single_dataset:
            result["single_dataset_info"] = datasets_info
        else:
            result["multi_datasets_info"] = datasets_info

        return result

    except Exception as e:
        error_msg = f"Error analyzing dataset: {e!s}"
        logger.exception(error_msg)
        return {
            "match_columns_retry_count": 0,
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
    regenerated_lookup = {}
    for dataset_assumption in regenerated_assumptions:
        dataset_name = dataset_assumption["dataset"]
        regenerated_lookup[dataset_name] = {}
        for column in dataset_assumption["columns"]:
            regenerated_lookup[dataset_name][column["name"]] = column

    merged_assumptions = []
    for dataset_assumption in existing_assumptions:
        dataset_name = dataset_assumption["dataset"]
        merged_columns = []

        for column in dataset_assumption["columns"]:
            column_name = column["name"]
            has_failed_searches = (
                dataset_name in failed_searches and column_name in failed_searches[dataset_name]
            )

            if (
                has_failed_searches
                and dataset_name in regenerated_lookup
                and column_name in regenerated_lookup[dataset_name]
            ):
                merged_columns.append(regenerated_lookup[dataset_name][column_name])
            else:
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

    # Handle both multi-dataset ("schemas") and single-dataset ("dataset_schema")
    dataset_schemas = datasets_info.get("schemas") or []
    if not dataset_schemas:
        single_schema = datasets_info.get("dataset_schema")
        if single_schema:
            dataset_schemas = [single_schema]

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


def route_from_match_columns(state: State) -> str:
    multi_datasets_info = state.get("multi_datasets_info", {})
    single_dataset_info = state.get("single_dataset_info", {})
    retry_count = state.get("match_columns_retry_count", 0)

    # Use whichever dataset info is available
    datasets_info = multi_datasets_info or single_dataset_info
    column_assumptions = datasets_info.get("column_assumptions") if datasets_info else None

    if column_assumptions and retry_count > 0 and retry_count < 3:
        logger.info(f"Routing back to match_columns for retry {retry_count}")
        return "match_columns"

    return "generate_sql"
