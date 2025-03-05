from langchain_core.tools import tool
import pandas as pd
import os
from typing import Dict, Any

@tool
def get_table_schema(table_name: str) -> Dict[str, Any]:
    """
    Get the schema of a specific table (column names and data types)

    Args:
        table_name: The name of the table/CSV file (with or without .csv extension)

    Returns:
        A dictionary with column names and their data types
    """
    if not table_name.endswith('.csv'):
        table_name += '.csv'

    data_dir = "./data"
    file_path = os.path.join(data_dir, table_name)

    if not os.path.exists(file_path):
        return {"error": f"Table '{table_name}' not found in the data directory"}

    try:
        df = pd.read_csv(file_path, nrows=5)

        schema = {}
        for column in df.columns:
            schema[column] = str(df[column].dtype)

        return {
            "table_name": table_name,
            "columns": list(df.columns),
            "schema": schema,
            "row_count": len(pd.read_csv(file_path, usecols=[0])),
        }
    except Exception as e:
        return {"error": f"Error reading table schema: {str(e)}"}

__tool__ = get_table_schema