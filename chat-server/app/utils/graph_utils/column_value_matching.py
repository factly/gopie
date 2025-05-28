import logging
from typing import Any

from app.services.gopie.sql_executor import execute_sql


async def match_column_values(
    column_assumptions: list[dict[str, Any]],
    dataset_name_mapping: dict[str, str],
) -> dict:
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
        Dictionary with verified values, and similar values suggestions
    """
    result = {
        "value_matches": {},
        "value_suggestions": {},
    }

    if not column_assumptions or not dataset_name_mapping:
        logging.warning("Empty column assumptions or dataset mapping provided")
        return result

    for dataset_assumption in column_assumptions:
        dataset_name = dataset_assumption.get("dataset")
        columns = dataset_assumption.get("columns", [])

        if not dataset_name or dataset_name not in dataset_name_mapping:
            logging.warning(
                f"Dataset '{dataset_name}' not found in mapping, skipping"
            )
            continue

        actual_table = dataset_name_mapping[dataset_name]

        for col_idx, column_obj in enumerate(columns):
            column_name = column_obj.get("name")
            exact_values = column_obj.get("exact_values", [])
            fuzzy_values = column_obj.get("fuzzy_values", [])

            if not column_name:
                logging.warning(
                    f"Skipping column {col_idx+1}: No column name provided"
                )
                continue

            if exact_values:
                await verify_exact_values(
                    column_name,
                    exact_values,
                    actual_table,
                    result,
                )

            if fuzzy_values:
                await verify_fuzzy_values(
                    column_name,
                    fuzzy_values,
                    actual_table,
                    result,
                )

    logging.debug(
        f"Column value matching completed with "
        f"{len(result['value_matches'])} value matches"
    )
    return result


async def verify_exact_values(
    column_name: str,
    exact_values: list[str],
    table_name: str,
    result: dict[str, Any],
) -> None:
    """
    Verify exact values against the column and collect matches.
    """
    matches = []

    for value in exact_values:
        exact_match = await check_exact_match(value, column_name, table_name)
        if exact_match:
            matches.append(value)

    if matches:
        result["value_matches"][column_name] = matches


async def verify_fuzzy_values(
    column_name: str,
    fuzzy_values: list[str],
    table_name: str,
    result: dict[str, Any],
) -> None:
    """
    Verify fuzzy values against the column and collect suggestions.
    """
    suggestions = {}

    for value in fuzzy_values:
        similar = await find_similar_values(value, column_name, table_name)
        if similar:
            suggestions[value] = similar

    if suggestions:
        if column_name not in result["value_suggestions"]:
            result["value_suggestions"][column_name] = {}

        result["value_suggestions"][column_name][
            "similar_values"
        ] = suggestions


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
            logging.info(f"Exact match found for '{value}' in '{column_name}'")
            return True
    except Exception as e:
        logging.error(
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
        logging.error(
            f"Error finding similar values for '{value}' in "
            f"'{table_name}.{column_name}': {str(e)}",
            exc_info=True,
        )

    if similar_values:
        logging.info(
            f"Found {len(similar_values)} similar values for '{value}'"
        )

    return list(set(similar_values))
