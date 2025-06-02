from app.core.log import logger
from app.models.data import ColumnValueMatching
from app.services.gopie.sql_executor import execute_sql


async def match_column_values(
    column_assumptions: list[dict],
    dataset_name_mapping: dict,
) -> ColumnValueMatching:
    """
    Match column values against exact and fuzzy values and find similar values
    when exact matches aren't found.

    Args:
        column_assumptions: List of dictionaries containing dataset and columns
            Each dict has 'dataset' and 'columns' keys, where 'columns' is a
            list of dictionaries with 'name', 'exact_values', and
            'fuzzy_values' keys.
        dataset_name_mapping: Mapping of user-friendly dataset names to actual
            table names

    Returns:
        ColumnValueMatching object with analyzed datasets, matched column
        values, and value suggestions for each dataset
    """
    result = ColumnValueMatching()

    if not column_assumptions or not dataset_name_mapping:
        logger.warning("Empty column assumptions or dataset mapping provided")
        return result

    for dataset_assumption in column_assumptions:
        dataset_name = dataset_assumption.get("dataset")
        columns = dataset_assumption.get("columns", [])

        if not dataset_name or dataset_name not in dataset_name_mapping:
            logger.warning(
                f"Dataset '{dataset_name}' not found in mapping, skipping"
            )
            continue

        dataset_analysis = ColumnValueMatching.DatasetAnalysis(
            dataset_name=dataset_name
        )
        result.datasets[dataset_name] = dataset_analysis

        actual_table = dataset_name_mapping[dataset_name]

        for col_idx, column_obj in enumerate(columns):
            column_name = column_obj.get("name")
            exact_values = column_obj.get("exact_values", [])
            fuzzy_values = column_obj.get("fuzzy_values", [])

            if not column_name:
                logger.warning(
                    f"Skipping column {col_idx + 1}: No column name provided"
                )
                continue

            column_entry = ColumnValueMatching.ColumnAnalysis(
                column_name=column_name
            )

            dataset_analysis.columns_analyzed.append(column_entry)

            if exact_values:
                await verify_exact_values(
                    column_entry,
                    column_name,
                    exact_values,
                    actual_table,
                )

            if fuzzy_values:
                await verify_fuzzy_values(
                    column_entry,
                    column_name,
                    fuzzy_values,
                    actual_table,
                )

    result.datasets = {
        k: v for k, v in result.datasets.items() if v.columns_analyzed
    }

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
        similar_values = await find_similar_values(
            value, column_name, table_name
        )

        suggestion = ColumnValueMatching.SuggestedAlternative(
            requested_value=value,
            match_type="fuzzy",
            found_similar_values=bool(similar_values),
            similar_values=similar_values,
        )

        column_entry.suggested_alternatives.append(suggestion)


async def check_exact_match(
    value: str, column_name: str, table_name: str
) -> bool:
    """
    Check if the value exactly matches any value in the column.
    """

    try:
        query = f"""
        SELECT COUNT(*) as count
        FROM {table_name}
        WHERE LOWER({column_name}) = LOWER('{value}')
        """
        result = await execute_sql(query)

        if (
            isinstance(result, list)
            and result
            and result[0].get("count", 0) > 0
        ):
            logger.debug(f"Exact match found for '{value}' in '{column_name}'")
            return True
    except Exception as e:
        logger.error(
            f"Error checking exact match for '{value}' in "
            f"'{table_name}.{column_name}': {str(e)}",
            exc_info=True,
        )

    return False


async def find_similar_values(
    value: str, column_name: str, table_name: str
) -> list[str]:
    """
    Find values in the column similar to the expected value.
    """

    similar_values = []

    try:
        query = f"""
        SELECT DISTINCT {column_name}
        FROM {table_name}
        WHERE {column_name} IS NOT NULL
          AND (
            LOWER({column_name}) LIKE LOWER('%{value}%')
            OR
            LOWER('{value}') LIKE LOWER(CONCAT('%', {column_name}, '%'))
          )
        LIMIT 5
        """
        result = await execute_sql(query)

        if result:
            for row in result:
                if column_name in row:
                    similar_values.append(row[column_name])

        # If no results, try word-by-word matching
        if not similar_values:
            words = value.split()

            if len(words) > 1:
                for word in words:
                    if len(word) < 3:  # Skip short words
                        continue

                    query = f"""
                    SELECT DISTINCT {column_name}
                    FROM {table_name}
                    WHERE {column_name} IS NOT NULL
                    AND LOWER({column_name}) LIKE LOWER('%{word}%')
                    LIMIT 5
                    """
                    word_result = await execute_sql(query)

                    if word_result:
                        for row in word_result:
                            if column_name in row:
                                similar_values.append(row[column_name])
    except Exception as e:
        logger.error(
            f"Error finding similar values for '{value}' in "
            f"'{table_name}.{column_name}': {str(e)}",
            exc_info=True,
        )

    return list(set(similar_values))
