from typing import Any

from app.workflow.node.execute_query import execute_sql


async def match_column_values(
    column_assumption: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Match assumed column values with actual dataset values using SQL queries.

    Args:
        column_assumption: List of dictionaries containing dataset and column
                          assumptions

    Returns:
        Dictionary with column mapping results
    """
    column_mappings = []

    for dataset_info in column_assumption:
        dataset_name = dataset_info.get("dataset")

        if not dataset_name:
            continue

        if dataset_name.endswith(".csv"):
            dataset_name = dataset_name[:-4]

        dataset_mapping = {"dataset": dataset_name, "columns": []}

        for column_info in dataset_info.get("columns", []):
            column_name = column_info.get("name")
            expected_values = column_info.get("expected_values", [])

            if not column_name or not expected_values:
                continue

            column_result = await verify_column_existence(
                dataset_name, column_name
            )

            if "error" in column_result:
                dataset_mapping["columns"].append(column_result)
                continue

            # Process expected values
            column_result["expected_name"] = column_name
            column_result["name"] = column_name

            # Get exact and similar matches for the expected values
            value_matches = await find_matching_values(
                dataset_name, column_name, expected_values
            )

            column_result.update(value_matches)
            dataset_mapping["columns"].append(column_result)

        column_mappings.append(dataset_mapping)

    return {"column_mappings": column_mappings}


async def verify_column_existence(
    dataset_name: str, column_name: str
) -> dict[str, Any]:
    """
    Verify if a column exists in the dataset using SQL query.

    Args:
        dataset_name: Name of the dataset
        column_name: Name of the column to verify

    Returns:
        Dictionary indicating if the column exists or not
    """
    try:
        # Query to check if column exists in table
        sql_query = f"SELECT {column_name} FROM {dataset_name} LIMIT 1"

        response = await execute_sql(sql_query)

        if isinstance(response, dict) and "error" in response:
            return {
                "name": column_name,
                "error": f"Column not found in dataset: {response['error']}",
            }

        return {"name": column_name}

    except Exception as e:
        return {
            "name": column_name,
            "error": f"Error verifying column: {str(e)}",
        }


async def find_matching_values(
    dataset_name: str, column_name: str, expected_values: list[str]
) -> dict[str, Any]:
    """
    Find exact and similar matches for expected values using SQL queries.

    Args:
        dataset_name: Name of the dataset
        column_name: Name of the column to check
        expected_values: List of expected values to match

    Returns:
        Dictionary with exact matches and similar matches
    """
    result = {
        "correct_values": [],
        "not_found_values": [],
        "similar_values": {},
    }

    # Get column statistics for processing
    stats = await get_column_stats(dataset_name, column_name)

    if stats.get("error"):
        return {"error": stats["error"]}

    result["total_unique_values"] = stats["count"]

    # Check for exact matches first
    exact_matches = await find_exact_matches(
        dataset_name, column_name, expected_values
    )

    for value in expected_values:
        if value in exact_matches:
            result["correct_values"].append(value)
        else:
            # If no exact match, look for similar values
            similar = await find_similar_values(
                dataset_name, column_name, value
            )

            if similar:
                # Limit to 20 similar values
                result["similar_values"][value] = similar[:20]
                # Use the closest match as the correct value
                result["correct_values"].append(similar[0])
            else:
                result["not_found_values"].append(value)

    if result["total_unique_values"] > 100:
        suggestion = (
            "Large number of unique values. Consider filtering or grouping."
        )
        result["suggestion"] = suggestion

    return result


async def get_column_stats(
    dataset_name: str, column_name: str
) -> dict[str, Any]:
    """
    Get column statistics using SQL query.

    Args:
        dataset_name: Name of the dataset
        column_name: Name of the column

    Returns:
        Dictionary with column statistics
    """
    try:
        sql_query = f"""
            SELECT COUNT(DISTINCT {column_name}) AS count
            FROM {dataset_name}
        """

        response = await execute_sql(sql_query)

        if isinstance(response, dict) and "error" in response:
            return {"error": response["error"]}

        if isinstance(response, list) and len(response) > 0:
            return {"count": response[0].get("count", 0)}

        return {"count": 0}

    except Exception as e:
        return {"error": f"Error getting column statistics: {str(e)}"}


async def find_exact_matches(
    dataset_name: str, column_name: str, expected_values: list[str]
) -> list[str]:
    """
    Find exact matches for expected values using SQL query.

    Args:
        dataset_name: Name of the dataset
        column_name: Name of the column
        expected_values: List of expected values to match

    Returns:
        List of matched values
    """
    if not expected_values:
        return []

    # Escape single quotes in values for SQL
    escaped_values = [value.replace("'", "''") for value in expected_values]
    values_str = ", ".join(escaped_values)

    sql_query = (
        f"SELECT DISTINCT {column_name} "
        f"FROM {dataset_name} "
        f"WHERE {column_name} IN ({values_str})"
    )

    try:
        response = await execute_sql(sql_query)

        if isinstance(response, list):
            return [
                row.get(column_name, "")
                for row in response
                if column_name in row
            ]

        return []

    except Exception:
        matches = []
        for value in expected_values:
            try:
                escaped_value = value.replace("'", "''")
                sql_query = (
                    f"SELECT DISTINCT {column_name} "
                    f"FROM {dataset_name} "
                    f"WHERE {column_name} = '{escaped_value}' "
                    f"LIMIT 1"
                )

                response = await execute_sql(sql_query)

                if isinstance(response, list) and len(response) > 0:
                    matches.append(value)

            except Exception:
                continue

        return matches


async def find_similar_values(
    dataset_name: str, column_name: str, value: str, max_results: int = 20
) -> list[str]:
    """
    Find similar values for a given value using SQL LIKE patterns.

    Args:
        dataset_name: Name of the dataset
        column_name: Name of the column
        value: Value to find similar matches for
        max_results: Maximum number of similar results to return

    Returns:
        List of similar values
    """
    # Try multiple patterns to find similar values
    patterns = []

    # Handle spaces vs underscores conversion
    modified_value = value.replace(" ", "_")
    patterns.append(modified_value)
    patterns.append(value.replace("_", " "))

    # Create LIKE patterns for partial matches
    terms = value.split()
    if len(terms) > 1:
        # Match first few words
        patterns.append(f"{terms[0]}%")
        if len(terms) > 2:
            patterns.append(f"{terms[0]} {terms[1]}%")

    # Add wildcard patterns
    patterns.append(f"%{value}%")

    similar_values = []

    for pattern in patterns:
        if len(similar_values) >= max_results:
            break

        escaped_pattern = pattern.replace("'", "''")
        sql_query = (
            f"SELECT DISTINCT {column_name} "
            f"FROM {dataset_name} "
            f"WHERE {column_name} LIKE '{escaped_pattern}' "
            f"LIMIT {max_results}"
        )

        try:
            response = await execute_sql(sql_query)

            if isinstance(response, list):
                new_values = [
                    row.get(column_name, "")
                    for row in response
                    if column_name in row
                ]
                # Add new values not already found
                for val in new_values:
                    if val and val not in similar_values:
                        similar_values.append(val)

        except Exception:
            continue

    return similar_values[:max_results]
