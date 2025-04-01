import os
from typing import Any, Dict

import pandas as pd
from langchain_core.tools import tool


@tool
def describe_table(table_name: str, include_all: bool = False) -> Dict[str, Any]:
    """
    Get statistical summary of numerical columns in a table

    Args:
        table_name: The name of the table/CSV file (with or without .csv extension)
        include_all: Whether to include all columns (not just numerical) in the summary

    Returns:
        Dictionary with statistical summaries of each column
    """
    if not table_name.endswith(".csv"):
        table_name += ".csv"

    data_dir = "./data"
    file_path = os.path.join(data_dir, table_name)

    if not os.path.exists(file_path):
        return {"error": f"Table '{table_name}' not found in the data directory"}

    try:
        df = pd.read_csv(file_path)

        info = {
            "table_name": table_name,
            "total_rows": len(df),
            "total_columns": len(df.columns),
        }

        if include_all:
            desc_df = df.describe(include="all")
        else:
            desc_df = df.describe()

        description = {}
        for column in desc_df.columns:
            description[column] = desc_df[column].to_dict()

        column_types = {}
        for column in df.columns:
            column_types[column] = str(df[column].dtype)

        result = {**info, "column_types": column_types, "statistics": description}

        return result
    except Exception as e:
        return {"error": f"Error describing table: {str(e)}"}


__tool__ = describe_table
