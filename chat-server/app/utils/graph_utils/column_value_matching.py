from app.core.log import logger
from app.models.data import ColumnValueMatching
from app.services.gopie.sql_executor import execute_sql
from app.workflow.graph.multi_dataset_graph.types import ColumnAssumptions


async def match_column_values(
    column_assumptions: list[ColumnAssumptions],
) -> ColumnValueMatching:
    """
    Match column values against exact and fuzzy values and find similar values
    when exact matches aren't found.

    Args:
        column_assumptions: List of dictionaries containing dataset and columns
            Each dict has 'dataset' and 'columns' keys, where 'columns' is a
            list of dictionaries with 'name', 'exact_values', and
            'fuzzy_values' keys.

    Returns:
        ColumnValueMatching object with analyzed datasets, matched column
        values, and value suggestions for each dataset
    """
    result = ColumnValueMatching()

    if not column_assumptions:
        logger.warning("Empty column assumptions provided")
        return result

    for dataset_assumption in column_assumptions:
        dataset_name = dataset_assumption.get("dataset")
        columns = dataset_assumption.get("columns", [])

        if not dataset_name:
            logger.warning("Dataset name not found in assumption, skipping")
            continue

        dataset_analysis = ColumnValueMatching.DatasetAnalysis(dataset_name=dataset_name)
        result.datasets[dataset_name] = dataset_analysis

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
                await verify_exact_values(
                    column_entry,
                    column_name,
                    exact_values,
                    dataset_name,
                )

            if fuzzy_values:
                await verify_fuzzy_values(
                    column_entry,
                    column_name,
                    fuzzy_values,
                    dataset_name,
                )

    result.datasets = {k: v for k, v in result.datasets.items() if v.columns_analyzed}

    result.summary = f"Analyzed values for {len(result.datasets)} datasets"
    return result


async def verify_exact_values(
    column_entry: ColumnValueMatching.ColumnAnalysis,
    column_name: str,
    exact_values: list,
    table_name: str,
) -> None:
    """
    Verify exact values against the column and collect matches.
    """
    for value in exact_values:
        exact_match = await check_exact_match(value, column_name, table_name)
        if exact_match:
            column_entry.verified_values.append(
                ColumnValueMatching.VerifiedValue(
                    value=value,
                    match_type="exact",
                    found_in_database=True,
                )
            )
        else:
            column_entry.verified_values.append(
                ColumnValueMatching.VerifiedValue(
                    value=value,
                    match_type="exact",
                    found_in_database=False,
                )
            )


async def verify_fuzzy_values(
    column_entry: ColumnValueMatching.ColumnAnalysis,
    column_name: str,
    fuzzy_values: list,
    table_name: str,
) -> None:
    """
    Verify fuzzy values against the column and collect suggestions.
    """
    for value in fuzzy_values:
        similar_values = await find_similar_values(value, column_name, table_name)

        suggestion = ColumnValueMatching.SuggestedAlternative(
            requested_value=value,
            match_type="fuzzy",
            found_similar_values=bool(similar_values),
            similar_values=similar_values,
        )

        column_entry.suggested_alternatives.append(suggestion)


async def check_exact_match(value: str, column_name: str, table_name: str) -> bool:
    """
    Check if the value exactly matches any value in the column.
    """

    try:
        query = f"""
        SELECT COUNT(*) as count
        FROM {table_name}
        WHERE LOWER({column_name}) = LOWER('{value}')
        """
        result = await execute_sql(query=query)

        if isinstance(result, list) and result:
            logger.debug(f"Exact match found for '{value}' in '{column_name}'")
            return True
    except Exception as e:
        logger.error(
            f"Error checking exact match for '{value}' in "
            f"'{table_name}.{column_name}': {str(e)}",
            exc_info=True,
        )

    return False


async def find_similar_values(value: str, column_name: str, table_name: str) -> list[str]:
    """
    Search for values in a database column that are similar to the specified value using a case-insensitive substring match.
    
    Parameters:
        value (str): The value to search for similar entries.
        column_name (str): The name of the column to search within.
        table_name (str): The name of the table containing the column.
    
    Returns:
        list[str]: A list of up to five distinct values from the column that contain the specified value as a substring, matched case-insensitively.
    """
    similar_values = []

    # First attempt: ILIKE matching (case-insensitive exact substring)
    try:
        query = f"""
        SELECT DISTINCT {column_name}
        FROM {table_name}
        WHERE {column_name} ILIKE '%{value}%'
        LIMIT 5
        """
        result = await execute_sql(query=query)

        if isinstance(result, list) and result:
            similar_values = [str(row.get(column_name)) for row in result if row]
            logger.debug(
                f"Found {len(similar_values)} ILIKE matches for '{value}' in '{column_name}'"
            )

    except Exception as e:
        logger.error(
            f"Error in ILIKE search for '{value}' in " f"'{table_name}.{column_name}': {str(e)}",
            exc_info=True,
        )

    # Fallback: Trigram similarity matching if no LIKE results found
    # if not similar_values:
    #     try:
    #         trigram_query = f"""
    #         SELECT DISTINCT {column_name}, similarity({column_name}, '{value}') as sim_score
    #         FROM {table_name}
    #         WHERE {column_name} % '{value}'
    #         ORDER BY sim_score DESC
    #         LIMIT 5
    #         """
    #         trigram_result = await execute_sql(query=trigram_query)

    #         if isinstance(trigram_result, list) and trigram_result:
    #             similar_values = [str(row.get(column_name)) for row in trigram_result if row]
    #             logger.debug(
    #                 f"Found {len(similar_values)} trigram matches for '{value}' in '{column_name}'
    # "
    #             )

    #     except Exception as e:
    #         logger.warning(
    #             f"Trigram similarity search failed for '{value}' in "
    #             f"'{table_name}.{column_name}': {str(e)}. "
    #             "This may indicate pg_trgm extension is not enabled.",
    #             exc_info=True,
    #         )

    return similar_values
