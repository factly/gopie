import os
from typing import Any, Dict

import pandas as pd
from langchain_core.tools import tool


@tool
def get_column_values(
    table_name: str, column_name: str, unique_only: bool = True, limit: int = 100
) -> Dict[str, Any]:
    """
    Get values from a specific column in a table, useful for filtering

    Args:
        table_name: The name of the table/CSV file (with or without .csv extension)
        column_name: The name of the column to get values from
        unique_only: Whether to return only unique values (default True)
        limit: Maximum number of values to return (default 100)

    Returns:
        Dictionary with column values and metadata
    """
    if not table_name.endswith(".csv"):
        table_name += ".csv"

    data_dir = "./data"
    file_path = os.path.join(data_dir, table_name)

    if not os.path.exists(file_path):
        return {"error": f"Table '{table_name}' not found in the data directory"}

    try:
        df = pd.read_csv(file_path)

        if column_name not in df.columns:
            return {
                "error": f"Column '{column_name}' not found in table '{table_name}'"
            }

        if unique_only:
            values = df[column_name].dropna().unique().tolist()
        else:
            values = df[column_name].dropna().tolist()

        values = values[:limit]
        value_type = str(df[column_name].dtype)

        stats = {}
        if pd.api.types.is_numeric_dtype(df[column_name]):
            stats = {
                "min": float(df[column_name].min()),
                "max": float(df[column_name].max()),
                "mean": float(df[column_name].mean()),
                "median": float(df[column_name].median()),
            }

        return {
            "table_name": table_name,
            "column_name": column_name,
            "values": values,
            "value_type": value_type,
            "unique_count": len(df[column_name].dropna().unique()),
            "total_count": len(df[column_name].dropna()),
            "has_null": bool(df[column_name].isna().sum() > 0),
            "null_count": int(df[column_name].isna().sum()),
            "statistics": stats,
        }
    except Exception as e:
        return {"error": f"Error getting column values: {str(e)}"}


__tool__ = get_column_values
