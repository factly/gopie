from typing import Any, Dict, List

import pandas as pd


def levenshtein_distance(str1, str2):
    """
    Calculate the Levenshtein distance between two strings using a memory-efficient approach.
    """
    m = len(str1)
    n = len(str2)

    prev_row = [j for j in range(n + 1)]
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


def find_closest_column_names(column_name, df_columns, max_distance=2):
    """
    Find closest matches for a column name in the dataframe columns using Levenshtein distance.

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

    suggestions = [col for col, dist in distance_map.items() if dist <= max_distance]
    suggestions.sort(key=lambda x: distance_map[x])

    return suggestions


def find_similar_values(expected_value, actual_values, max_distance=2):
    """
    Find similar values to the expected value in the actual values using Levenshtein distance
    and substring matching.

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

        # Check for substring match first
        if expected_lower in val_lower or val_lower in expected_lower:
            # Give a low distance for substring matches
            distance = 0.5
        else:
            # Fall back to Levenshtein distance
            distance = levenshtein_distance(expected_lower, val_lower)

        distance_map[val] = distance

    # Get values within the maximum distance
    similar_values = [val for val, dist in distance_map.items() if dist <= max_distance]
    similar_values.sort(key=lambda x: distance_map[x])  # Sort by similarity

    return similar_values


def correct_column_values(
    column_assumption: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Find the correct column values that match or are similar to the expected values in the datasets.

    Args:
        column_assumption (List[Dict[str, Any]]):
            [
                {
                    "dataset": "dataset_name1",
                    "columns": [
                        {
                            "name": "column_name",
                            "expected_values": ["value1", "value2"] or "range: min-max",
                            "filter_condition": "equals" or "range" or "none"
                        }
                    ]
                }
            ]
    Returns:
        Dict[str, Any]: Column mappings with the correct values that exist in the dataset
    """
    import os

    column_mappings = []

    for dataset_info in column_assumption:
        dataset_name = dataset_info.get("dataset")

        if not dataset_name:
            continue

        if not dataset_name.endswith(".csv"):
            dataset_name += ".csv"

        data_dir = "./data"
        file_path = os.path.join(data_dir, dataset_name)

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

                    unique_values = (
                        df[column_name].fillna("NA").astype(str).unique().tolist()
                    )
                    column_result["unique_values"] = unique_values[:20]
                    column_result["total_unique_values"] = len(unique_values)

                    correct_column_values = []

                    for value in expected_values:
                        if value not in unique_values:
                            similar_vals = find_similar_values(value, unique_values)
                            if similar_vals:
                                column_result.setdefault("similar_values", {})[
                                    value
                                ] = similar_vals[:20]
                                correct_column_values.append(similar_vals[0])
                            else:
                                column_result.setdefault("not_found_values", []).append(
                                    value
                                )
                        else:
                            correct_column_values.append(value)

                    column_result["correct_values"] = correct_column_values
                else:
                    column_result["error"] = "Column name not found in dataset"

                dataset_mapping["columns"].append(column_result)

            column_mappings.append(dataset_mapping)

        except Exception as e:
            column_mappings.append(
                {
                    "dataset": dataset_name,
                    "error": f"Error processing dataset: {str(e)}",
                    "columns": [],
                }
            )

    return {"column_mappings": column_mappings}
