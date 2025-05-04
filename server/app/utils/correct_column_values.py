import os
from typing import Any

import pandas as pd

DEFAULT_MAX_DISTANCE = 10
MAX_UNIQUE_VALUES_TO_RETURN = 20


def levenshtein_distance(str1: str, str2: str) -> int:
    """
    Calculate the Levenshtein distance between two strings using a
    memory-efficient approach.

    Args:
        str1: First string to compare
        str2: Second string to compare

    Returns:
        The edit distance between the two strings
    """
    m = len(str1)
    n = len(str2)

    prev_row = list(range(n + 1))
    curr_row = [0] * (n + 1)

    for i in range(1, m + 1):
        curr_row[0] = i

        for j in range(1, n + 1):
            if str1[i - 1] == str2[j - 1]:
                curr_row[j] = prev_row[j - 1]
            else:
                curr_row[j] = 1 + min(
                    curr_row[j - 1],
                    prev_row[j],
                    prev_row[j - 1],
                )

        prev_row = curr_row.copy()

    return curr_row[n]


def find_closest_column_names(
    column_name: str,
    df_columns: list[str],
    max_distance: int = DEFAULT_MAX_DISTANCE,
) -> list[str]:
    """
    Find closest matches for a column name in the dataframe columns using
    Levenshtein distance.

    Args:
        column_name: The column name to match
        df_columns: List of actual column names in the dataframe
        max_distance: Maximum allowed Levenshtein distance for suggestions

    Returns:
        List of closest column name matches
    """
    distance_map = {}
    for col in df_columns:
        distance = levenshtein_distance(column_name.lower(), col.lower())
        distance_map[col] = distance

    suggestions = [
        col for col, dist in distance_map.items() if dist <= max_distance
    ]
    suggestions.sort(key=lambda x: distance_map[x])

    return suggestions


def find_similar_values(
    expected_value: Any,
    actual_values: list[Any],
    max_distance: int = DEFAULT_MAX_DISTANCE,
) -> list[str]:
    """
    Find similar values to the expected value in the actual values
    using Levenshtein distance and substring matching. Words separated
    by spaces are joined before comparison.

    Args:
        expected_value: The value to match
        actual_values: List of actual values in the column
        max_distance: Maximum allowed Levenshtein distance for suggestions

    Returns:
        List of similar values sorted by similarity
    """
    distance_map = {}

    if not isinstance(expected_value, str):
        expected_value = str(expected_value)

    expected_lower = expected_value.lower()

    for val in actual_values:
        if not isinstance(val, str):
            val = str(val)

        val_lower = val.lower()

        if expected_lower in val_lower or val_lower in expected_lower:
            distance = 0.5
        else:
            distance = levenshtein_distance(expected_lower, val_lower)

        distance_map[val] = distance

    similar_values = [
        val for val, dist in distance_map.items() if dist <= max_distance
    ]
    similar_values.sort(key=lambda x: distance_map[x])

    return similar_values


def correct_column_values(
    column_assumption: list[dict[str, Any]],
) -> dict[str, Any]:
    column_mappings = []

    for dataset_info in column_assumption:
        dataset_name = dataset_info.get("dataset")

        if not dataset_name:
            continue

        if not dataset_name.endswith(".csv"):
            dataset_name += ".csv"

        file_path = os.path.join("", dataset_name)

        if not os.path.exists(file_path):
            column_mappings.append(
                {
                    "dataset": dataset_name,
                    "error": f"Dataset '{dataset_name}' not found",
                    "columns": [],
                }
            )
            continue

        try:
            df = pd.read_csv(file_path)
            dataset_mapping = {"dataset": dataset_name, "columns": []}

            for column_info in dataset_info.get("columns", []):
                column_name = column_info.get("name")
                expected_values = column_info.get("expected_values", [])

                column_result = {}

                if column_name in df.columns:
                    column_result["name"] = column_name
                    column_result["expected_name"] = column_name

                    unique_values = (
                        df[column_name]
                        .fillna("NA")
                        .astype(str)
                        .unique()
                        .tolist()
                    )

                    mapped_expected_values = {}
                    for value in expected_values:
                        new_value = value.replace(" ", "_")
                        mapped_expected_values[new_value] = value

                    mapped_unique_dict = {}
                    for value in unique_values:
                        new_value = value.replace(" ", "_")
                        mapped_unique_dict[new_value] = value

                    mapped_unique_values = list(mapped_unique_dict.keys())
                    column_result["total_unique_values"] = len(unique_values)

                    if len(unique_values) > 100:
                        column_result["suggestion"] = (
                            "Large number of unique values. Consider "
                            "filtering or grouping."
                        )

                    correct_column_values = []

                    for value in expected_values:
                        new_value = value.replace(" ", "_")
                        if new_value in mapped_unique_values:
                            correct_column_values.append(
                                mapped_unique_dict[new_value]
                            )
                        else:
                            similar_mapped_vals = find_similar_values(
                                new_value, mapped_unique_values
                            )
                            if similar_mapped_vals:
                                similar_original_vals = [
                                    mapped_unique_dict[val]
                                    for val in similar_mapped_vals
                                ]

                                column_result.setdefault("similar_values", {})[
                                    value
                                ] = similar_original_vals[
                                    :MAX_UNIQUE_VALUES_TO_RETURN
                                ]

                                correct_column_values.append(
                                    similar_original_vals[0]
                                )
                            else:
                                column_result.setdefault(
                                    "not_found_values", []
                                ).append(value)

                    column_result["correct_values"] = correct_column_values
                else:
                    column_result["error"] = "Column name not found in dataset"

                dataset_mapping["columns"].append(column_result)

            column_mappings.append(dataset_mapping)

        except Exception as e:
            column_mappings.append(
                {
                    "dataset": dataset_name,
                    "error": f"Error processing dataset: {e!s}",
                    "columns": [],
                }
            )

    return {"column_mappings": column_mappings}
