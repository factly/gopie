import logging
from typing import Any

from server.app.services.gopie.sql_executor import execute_sql


async def match_column_values(
    column_assumptions: list[dict[str, Any]],
    dataset_name_mapping: dict[str, str],
) -> dict[str, Any]:
    """
    Match column values against expected values and find similar values
    when exact matches aren't found.

    Args:
        column_assumptions: List of dictionaries containing dataset and columns
            Each dict has 'dataset' and 'columns' keys, where 'columns' is a
            list of dictionaries with 'name' and 'expected_values' keys.
        dataset_name_mapping: Mapping of user-friendly dataset names to actual
            table names

    Returns:
        Dictionary with matched columns, verified values, and suggestions
    """
    logging.info(
        f"Starting column value matching with {len(column_assumptions)} "
        "dataset assumptions"
    )
    logging.debug(f"Column assumptions: {column_assumptions}")
    logging.debug(f"Dataset name mapping: {dataset_name_mapping}")

    result = {
        "value_matches": {},
        "value_suggestions": {},
        "column_mappings": {},
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
            expected_values = column_obj.get("expected_values", [])

            if not column_name:
                logging.warning(
                    f"Skipping column {col_idx+1}: No column name provided"
                )
                continue

            if expected_values:
                await verify_column_values(
                    column_name,
                    column_name,
                    expected_values,
                    actual_table,
                    result,
                )

    logging.info(
        f"Column value matching completed with "
        f"{len(result['value_matches'])} value matches"
    )
    return result


async def get_all_columns(
    dataset_name_mapping: dict[str, str],
) -> dict[str, set[str]]:
    """Get all column names from all tables in the dataset mapping."""
    result = {}

    for _, actual_table in dataset_name_mapping.items():
        try:
            query = f"""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = '{actual_table}'
            """
            columns_result = await execute_sql(query)

            if isinstance(columns_result, list) and columns_result:
                result[actual_table] = {
                    col["column_name"]
                    for col in columns_result
                    if "column_name" in col
                }
                logging.debug(
                    f"Found {len(result[actual_table])} columns for "
                    f"table '{actual_table}'"
                )
        except Exception as e:
            logging.error(
                f"Error getting columns for table '{actual_table}': {str(e)}",
                exc_info=True,
            )

    return result


def find_similar_column_names(
    column_name: str, columns: set[str]
) -> list[str]:
    """Find columns with names similar to the given column name."""
    similar_columns = []

    col_lower = column_name.lower()
    name_parts = col_lower.split("_")

    for col in columns:
        target_lower = col.lower()
        # Check for similarity
        if (
            col_lower in target_lower
            or target_lower in col_lower
            or any(word in target_lower for word in name_parts)
        ):
            similar_columns.append(col)

    return similar_columns


async def verify_column_values(
    original_column: str,
    verified_column: str,
    expected_values: list[str],
    table_name: str,
    result: dict[str, Any],
) -> None:
    """
    Verify expected values against the column and collect matches/suggestions.
    """

    logging.info(
        f"Verifying {len(expected_values)} values for '{verified_column}'"
    )

    matches = []
    suggestions = {}

    for value in expected_values:
        # Try exact match
        exact_match = await check_exact_match(
            value, verified_column, table_name
        )

        if exact_match:
            matches.append(value)
        else:
            # Try approximate matches
            similar = await find_similar_values(
                value, verified_column, table_name
            )
            if similar:
                suggestions[value] = similar

    # Store results
    if matches:
        result["value_matches"][original_column] = matches

    if suggestions:
        if original_column not in result["value_suggestions"]:
            result["value_suggestions"][original_column] = {}

        result["value_suggestions"][original_column][
            "similar_values"
        ] = suggestions


async def check_exact_match(
    value: str, column_name: str, table_name: str
) -> bool:
    """Check if the value exactly matches any value in the column."""
    try:
        safe_value = value.replace("'", "''")
        query = f"""
        SELECT COUNT(*) as count
        FROM {table_name}
        WHERE LOWER({column_name}) = LOWER('{safe_value}')
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
    """Find values in the column similar to the expected value."""
    similar_values = []

    try:
        safe_value = value.replace("'", "''")

        # Try LIKE search
        query = f"""
        SELECT DISTINCT {column_name}
        FROM {table_name}
        WHERE {column_name} IS NOT NULL
          AND (
            LOWER({column_name}) LIKE LOWER('%{safe_value}%')
            OR
            LOWER('{safe_value}') LIKE LOWER(CONCAT('%', {column_name}, '%'))
          )
        LIMIT 5
        """
        result = await execute_sql(query)

        if isinstance(result, list) and result:
            for row in result:
                if column_name in row:
                    similar_values.append(row[column_name])

        # If no results, try word-by-word matching
        if not similar_values:
            words = safe_value.split()
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

                if isinstance(word_result, list) and word_result:
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
