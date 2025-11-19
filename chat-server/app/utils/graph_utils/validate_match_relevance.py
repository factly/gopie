from langchain_core.runnables import RunnableConfig
from langsmith import traceable
from pydantic import BaseModel, Field

from app.core.log import custom_logger as logger
from app.models.data import ColumnValueMatching
from app.utils.langsmith.prompt_manager import get_prompt_llm_chain


class MatchValidation(BaseModel):
    dataset_name: str
    column_name: str
    fuzzy_value_searched: str
    is_relevant: bool = Field(description="True if relevance_score >= 70, False otherwise")
    relevance_score: float = Field(description="Relevance score from 0-100")
    reasoning: str = Field(description="Brief explanation of the evaluation (1-2 sentences)")
    relevant_values: list[str] = Field(
        description="List of values that are actually relevant (max 3), filtered from the matched values",
        default_factory=list,
    )


class BatchValidationOutput(BaseModel):
    validations: list[MatchValidation] = Field(
        description="List of validation results for each fuzzy match"
    )


@traceable(run_type="tool", name="validate_match_relevance")
async def validate_match_relevance(  # noqa: C901
    analyze_dataset_result: ColumnValueMatching,
    user_query: str,
    config: RunnableConfig,
) -> ColumnValueMatching:
    """
    Validate fuzzy match relevance for all Levenshtein matches in a single LLM call.

    This function:
    1. Marks all ILIKE matches as trusted (100% relevant)
    2. Collects all Levenshtein matches
    3. Validates them in a single batch LLM call
    4. Updates the analyze_dataset_result with validation results

    Args:
        analyze_dataset_result: The ColumnValueMatching result from match_column_values
        user_query: The original user query for context
        config: Runnable configuration

    Returns:
        Updated ColumnValueMatching with relevance scores and filtered values
    """
    matches_to_validate = []

    for dataset_name, dataset_analysis in analyze_dataset_result.datasets.items():
        for column_analysis in dataset_analysis.columns_analyzed:
            for suggestion in column_analysis.suggested_alternatives:
                if suggestion.match_source == "levenshtein" and suggestion.found_similar_values:
                    matches_to_validate.append(
                        {
                            "dataset_name": dataset_name,
                            "column_name": column_analysis.column_name,
                            "fuzzy_value_searched": suggestion.requested_value,
                            "matched_values": suggestion.similar_values,
                        }
                    )

    if not matches_to_validate:
        logger.debug("No Levenshtein matches to validate")
        return analyze_dataset_result

    try:
        logger.info(f"Validating {len(matches_to_validate)} fuzzy matches with LLM in batch...")

        # Format matches for prompt
        formatted_matches = []
        for i, match in enumerate(matches_to_validate, 1):
            formatted_matches.append(
                f"{i}. Dataset: {match['dataset_name']}\n"
                f"   Column: {match['column_name']}\n"
                f"   User searched for: '{match['fuzzy_value_searched']}'\n"
                f"   Levenshtein matched values: {match['matched_values']}"
            )

        fuzzy_matches = "\n\n".join(formatted_matches)

        input_str = f"""
User Query: {user_query}

Fuzzy Matches to Validate:
{fuzzy_matches}
        """

        chain = get_prompt_llm_chain(
            "validate_match_relevance",
            config,
            schema=BatchValidationOutput,
        )

        response = await chain.ainvoke({"input": input_str})

        validation_lookup = {}
        for validation in response.validations:
            key = (
                validation.dataset_name,
                validation.column_name,
                validation.fuzzy_value_searched,
            )
            validation_lookup[key] = validation

        for dataset_name, dataset_analysis in analyze_dataset_result.datasets.items():
            for column_analysis in dataset_analysis.columns_analyzed:
                for suggestion in column_analysis.suggested_alternatives:
                    if suggestion.match_source == "levenshtein" and suggestion.found_similar_values:
                        key = (
                            dataset_name,
                            column_analysis.column_name,
                            suggestion.requested_value,
                        )
                        validation = validation_lookup.get(key)

                        if validation:
                            suggestion.is_relevant = validation.is_relevant
                            suggestion.relevance_score = validation.relevance_score

                            if validation.is_relevant and validation.relevant_values:
                                suggestion.similar_values = validation.relevant_values[:3]
                                logger.info(
                                    f"✓ Fuzzy match: '{suggestion.requested_value}' → "
                                    f"{len(suggestion.similar_values)} relevant values → "
                                    f"{validation.relevance_score:.0f}%"
                                )
                            else:
                                suggestion.similar_values = []
                                suggestion.found_similar_values = False
                                logger.info(
                                    f"✗ Fuzzy match: '{suggestion.requested_value}' → "
                                    f"no relevant values → {validation.relevance_score:.0f}%"
                                )

                            logger.debug(f"Reasoning: {validation.reasoning}")
                        else:
                            suggestion.is_relevant = False
                            suggestion.relevance_score = 0.0
                            suggestion.similar_values = []
                            suggestion.found_similar_values = False
                            logger.warning(
                                f"No validation result for '{suggestion.requested_value}' "
                                f"in {dataset_name}.{column_analysis.column_name}"
                            )

        logger.info(f"Batch validation complete: {len(response.validations)} matches processed")

    except Exception as e:
        logger.exception(f"Error in batch validation: {e!s}")
        for dataset_name, dataset_analysis in analyze_dataset_result.datasets.items():
            for column_analysis in dataset_analysis.columns_analyzed:
                for suggestion in column_analysis.suggested_alternatives:
                    if suggestion.match_source == "levenshtein" and suggestion.found_similar_values:
                        suggestion.is_relevant = False
                        suggestion.relevance_score = 0.0

    return analyze_dataset_result
