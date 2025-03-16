from typing import Any, Dict

import pandas as pd
from langchain_core.tools import tool


@tool
def validate_column_values(
    dataset_name: str,
    column_name: str,
    expected_values: Any = None,
    filter_condition: str = None,
) -> Dict[str, Any]:
    """
    Validate column values against expected values or conditions and identify data quality issues.

    Args:
        dataset_name: The name of the dataset/CSV file (with or without .csv extension)
        column_name: The name of the column to validate
        expected_values: Expected values or range for the column (optional)
        filter_condition: Expected filter condition (e.g., equals, greater than) (optional)

    Returns:
        Dictionary with validation results and recommendations
    """
    import os

    if not dataset_name.endswith(".csv"):
        dataset_name += ".csv"

    data_dir = "./data"
    file_path = os.path.join(data_dir, dataset_name)

    if not os.path.exists(file_path):
        return {"error": f"Dataset '{dataset_name}' not found"}

    try:
        # Read the dataset
        df = pd.read_csv(file_path)

        if column_name not in df.columns:
            return {
                "error": f"Column '{column_name}' not found in dataset '{dataset_name}'"
            }

        # Get column data
        column_data = df[column_name]

        # Basic validation
        validation_results = {
            "dataset": dataset_name,
            "column": column_name,
            "data_type": str(column_data.dtype),
            "null_count": int(column_data.isna().sum()),
            "null_percentage": float(column_data.isna().mean() * 100),
            "unique_count": len(column_data.dropna().unique()),
            "total_count": len(column_data),
            "issues": [],
            "recommendations": [],
        }

        # Check for null values
        if validation_results["null_count"] > 0:
            validation_results["issues"].append(
                {
                    "type": "null_values",
                    "description": f"Column contains {validation_results['null_count']} null values ({validation_results['null_percentage']:.2f}%)",
                }
            )

            if validation_results["null_percentage"] > 50:
                validation_results["recommendations"].append(
                    "High percentage of null values. Consider if this column is appropriate for the query."
                )
            elif validation_results["null_percentage"] > 10:
                validation_results["recommendations"].append(
                    "Moderate percentage of null values. Consider adding NULL handling in your query."
                )

        # Check data type appropriateness
        if pd.api.types.is_numeric_dtype(column_data):
            # For numeric columns
            validation_results["statistics"] = {
                "min": float(column_data.min())
                if not pd.isna(column_data.min())
                else None,
                "max": float(column_data.max())
                if not pd.isna(column_data.max())
                else None,
                "mean": float(column_data.mean())
                if not pd.isna(column_data.mean())
                else None,
                "median": float(column_data.median())
                if not pd.isna(column_data.median())
                else None,
                "std": float(column_data.std())
                if not pd.isna(column_data.std())
                else None,
            }

            # Check for outliers using IQR method
            Q1 = column_data.quantile(0.25)
            Q3 = column_data.quantile(0.75)
            IQR = Q3 - Q1
            outlier_count = (
                (column_data < (Q1 - 1.5 * IQR)) | (column_data > (Q3 + 1.5 * IQR))
            ).sum()

            if outlier_count > 0:
                outlier_percentage = (outlier_count / len(column_data)) * 100
                validation_results["issues"].append(
                    {
                        "type": "outliers",
                        "description": f"Column contains {outlier_count} outliers ({outlier_percentage:.2f}%)",
                    }
                )

                if outlier_percentage > 5:
                    validation_results["recommendations"].append(
                        "Significant number of outliers detected. Consider adding range filters in your query."
                    )

        elif pd.api.types.is_string_dtype(column_data):
            # For string columns
            validation_results["statistics"] = {
                "empty_string_count": int((column_data == "").sum()),
                "max_length": int(column_data.str.len().max())
                if not pd.isna(column_data.str.len().max())
                else 0,
                "min_length": int(column_data.str.len().min())
                if not pd.isna(column_data.str.len().min())
                else 0,
            }

            # Check for inconsistent casing
            if validation_results["unique_count"] > 1:
                lowercase_count = len(column_data.str.lower().dropna().unique())
                if lowercase_count < validation_results["unique_count"]:
                    validation_results["issues"].append(
                        {
                            "type": "inconsistent_casing",
                            "description": f"Column has inconsistent casing. {validation_results['unique_count']} unique values reduce to {lowercase_count} when lowercased.",
                        }
                    )
                    validation_results["recommendations"].append(
                        "Consider using case-insensitive comparisons in your query (e.g., LOWER() function)."
                    )

        elif pd.api.types.is_datetime64_dtype(column_data):
            # For datetime columns
            validation_results["statistics"] = {
                "min_date": str(column_data.min())
                if not pd.isna(column_data.min())
                else None,
                "max_date": str(column_data.max())
                if not pd.isna(column_data.max())
                else None,
            }

        # Validate against expected values if provided
        if expected_values is not None:
            validation_results["expected_values_validation"] = {
                "expected_values": expected_values,
                "filter_condition": filter_condition,
                "issues": [],
            }

            if isinstance(expected_values, list) and expected_values:
                # Check if expected values exist in the column
                missing_values = [
                    v for v in expected_values if v not in column_data.values
                ]
                if missing_values:
                    validation_results["expected_values_validation"]["issues"].append(
                        {
                            "type": "missing_expected_values",
                            "description": f"Some expected values are not present in the column: {missing_values}",
                        }
                    )
                    validation_results["recommendations"].append(
                        "Some expected filter values don't exist in the data. Verify your filter conditions."
                    )

            elif (
                isinstance(expected_values, str) and "range:" in expected_values.lower()
            ):
                # Validate range
                try:
                    range_parts = (
                        expected_values.lower().replace("range:", "").strip().split("-")
                    )
                    min_val = float(range_parts[0].strip())
                    max_val = float(range_parts[1].strip())

                    if not pd.api.types.is_numeric_dtype(column_data):
                        validation_results["expected_values_validation"][
                            "issues"
                        ].append(
                            {
                                "type": "type_mismatch",
                                "description": f"Range filter specified but column is not numeric (type: {validation_results['data_type']})",
                            }
                        )
                        validation_results["recommendations"].append(
                            "Range filter cannot be applied to non-numeric column. Consider changing your filter approach."
                        )
                    else:
                        actual_min = validation_results["statistics"]["min"]
                        actual_max = validation_results["statistics"]["max"]

                        if min_val < actual_min:
                            validation_results["expected_values_validation"][
                                "issues"
                            ].append(
                                {
                                    "type": "range_mismatch",
                                    "description": f"Specified minimum value {min_val} is less than actual minimum {actual_min}",
                                }
                            )

                        if max_val > actual_max:
                            validation_results["expected_values_validation"][
                                "issues"
                            ].append(
                                {
                                    "type": "range_mismatch",
                                    "description": f"Specified maximum value {max_val} is greater than actual maximum {actual_max}",
                                }
                            )
                except Exception as e:
                    validation_results["expected_values_validation"]["issues"].append(
                        {
                            "type": "invalid_range",
                            "description": f"Could not parse range: {str(e)}",
                        }
                    )

        # Overall validation status
        if not validation_results["issues"] and (
            "expected_values_validation" not in validation_results
            or not validation_results["expected_values_validation"]["issues"]
        ):
            validation_results["status"] = "valid"
        else:
            validation_results["status"] = "issues_found"

        return validation_results

    except Exception as e:
        return {"error": f"Error validating column values: {str(e)}"}


__tool__ = validate_column_values
