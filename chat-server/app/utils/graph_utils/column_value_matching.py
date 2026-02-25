import asyncio

from langsmith import traceable

from app.core.log import custom_logger as logger
from app.models.data import ColumnValueMatching
from app.services.gopie.sql_executor import execute_sql
from app.utils.olap import get_query_builder
from app.workflow.graph.sql_planner_graph.types import ColumnAssumptions


def _is_valid_fuzzy_value(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


@traceable(run_type="tool", name="match_column_values")
async def match_column_values(
    column_assumptions: list[ColumnAssumptions],
    org_id: str,
    user_id: str,
) -> ColumnValueMatching:
    """
    Match column values against fuzzy values and find similar values.
    Exact values are trusted directly without validation.

    Args:
        column_assumptions: List of dictionaries containing dataset and columns
            Each dict has 'dataset' and 'columns' keys, where 'columns' is a
            list of dictionaries with 'name', 'exact_values', and
            'fuzzy_values' keys.
        org_id: Organization ID for multi-tenant support
        user_id: User ID for request authentication

    Returns:
        ColumnValueMatching object with analyzed datasets and value suggestions
        for each dataset
    """
    result = ColumnValueMatching()

    if not column_assumptions:
        logger.warning("Empty column assumptions provided")
        return result

    async def process_dataset(dataset_assumption):
        """Process a single dataset and return its analysis."""
        dataset_name = dataset_assumption.get("dataset")
        columns = dataset_assumption.get("columns", [])

        if not dataset_name:
            logger.warning("Dataset name not found in assumption, skipping")
            return None

        dataset_analysis = ColumnValueMatching.DatasetAnalysis(dataset_name=dataset_name)

        # Collect fuzzy verification tasks for parallel execution
        fuzzy_tasks = []

        for col_idx, column_obj in enumerate(columns):
            column_name = column_obj.get("name")
            exact_values = column_obj.get("exact_values", [])
            fuzzy_values = column_obj.get("fuzzy_values", [])

            if not column_name:
                logger.warning(f"Skipping column {col_idx + 1}: No column name provided")
                continue

            column_entry = ColumnValueMatching.ColumnAnalysis(column_name=column_name)

            dataset_analysis.columns_analyzed.append(column_entry)

            if exact_values:
                for value in exact_values:
                    column_entry.verified_values.append(
                        ColumnValueMatching.VerifiedValue(
                            value=value,
                            match_type="exact",
                            found_in_database=True,
                        )
                    )
                logger.debug(f"Trusted {len(exact_values)} exact values for '{column_name}'")

            if fuzzy_values:
                fuzzy_tasks.append(
                    verify_fuzzy_values(
                        column_entry=column_entry,
                        column_name=column_name,
                        fuzzy_values=fuzzy_values,
                        table_name=dataset_name,
                        org_id=org_id,
                        user_id=user_id,
                    )
                )

        # Execute all fuzzy verifications concurrently for this dataset
        if fuzzy_tasks:
            await asyncio.gather(*fuzzy_tasks)

        return dataset_name, dataset_analysis

    # Process all datasets concurrently
    dataset_results = await asyncio.gather(*[process_dataset(ds) for ds in column_assumptions])

    # Collect results, filtering out None values (skipped datasets)
    for dataset_result in dataset_results:
        if dataset_result is not None:
            dataset_name, dataset_analysis = dataset_result
            result.datasets[dataset_name] = dataset_analysis

    result.datasets = {k: v for k, v in result.datasets.items() if v.columns_analyzed}

    result.summary = f"Analyzed values for {len(result.datasets)} datasets"
    return result


@traceable(run_type="tool", name="verify_fuzzy_values")
async def verify_fuzzy_values(
    column_entry: ColumnValueMatching.ColumnAnalysis,
    column_name: str,
    fuzzy_values: list,
    table_name: str,
    org_id: str,
    user_id: str,
) -> None:
    """
    Verify fuzzy values against the column and collect suggestions.
    Invalid values are marked as failed to trigger fuzzy value regeneration.

    Args:
        column_entry: Column analysis entry to populate
        column_name: Name of the column
        fuzzy_values: List of fuzzy values to verify
        table_name: Name of the table
        org_id: Organization ID for multi-tenant support
        user_id: User ID for request authentication
    """

    for value in fuzzy_values:
        if not _is_valid_fuzzy_value(value):
            logger.warning(f"Invalid fuzzy value: {value} (type: {type(value).__name__})")
            continue

        str_value = str(value).strip()
        similar_values, match_source, error_message = await find_similar_values(
            value=str_value,
            column_name=column_name,
            table_name=table_name,
            org_id=org_id,
            user_id=user_id,
        )

        column_entry.suggested_alternatives.append(
            ColumnValueMatching.SuggestedAlternative(
                requested_value=str_value,
                match_type="fuzzy",
                found_similar_values=bool(similar_values),
                similar_values=similar_values,
                match_source=match_source,
                error_message=error_message,
            )
        )


@traceable(run_type="tool", name="find_similar_values")
async def find_similar_values(
    value: str,
    column_name: str,
    table_name: str,
    org_id: str,
    user_id: str,
) -> tuple[list[str], str, str | None]:
    """
    Search for similar values in database column using ILIKE, fallback to Levenshtein.
    Returns (list of similar values, match source, error message if any).

    Args:
        value: Value to search for
        column_name: Name of the column to search
        table_name: Name of the table
        org_id: Organization ID for multi-tenant support
        user_id: User ID for request authentication
    """
    escaped_value = value.replace("'", "''")
    builder = get_query_builder()

    try:
        query = builder.build_ilike_query(table_name, column_name, escaped_value, limit=5)
        result = await execute_sql(query=query, org_id=org_id, user_id=user_id)

        if isinstance(result, list) and result:
            similar_values = [str(row.get(column_name)) for row in result if row]
            logger.debug(f"Found {len(similar_values)} ILIKE matches for '{value}'")
            return similar_values, "ilike", None

    except Exception as e:
        error_msg = str(e)
        logger.error(f"ILIKE search failed for '{value}': {error_msg}")
        return [], "sql_error", error_msg

    try:
        query = builder.build_levenshtein_query(table_name, column_name, escaped_value, limit=5)
        result = await execute_sql(query=query, org_id=org_id, user_id=user_id)

        if isinstance(result, list) and result:
            similar_values = [str(row.get(column_name)) for row in result if row]
            logger.debug(f"Found {len(similar_values)} Levenshtein matches for '{value}'")
            return similar_values, "levenshtein", None

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Levenshtein search failed for '{value}': {error_msg}")
        return [], "sql_error", error_msg

    return [], "none", None
