import os
from typing import List

import pandas as pd

from src.lib.graph.types import ColumnSchema, DatasetSchema

DATA_DIR = "./data"


def get_dataset_preview(dataset_name: str, sample_rows: int = 3) -> DatasetSchema:
    """
    Get metadata and sample data from a dataset.
    """
    try:
        matching_files = [
            f
            for f in os.listdir(DATA_DIR)
            if f.endswith(".csv") and dataset_name.lower() in f.lower()
        ]

        if not matching_files:
            raise FileNotFoundError(f"Dataset not found: {dataset_name}")

        file_path = os.path.join(DATA_DIR, matching_files[0])
        df = pd.read_csv(file_path)

        file_size = os.path.getsize(file_path) / (1024 * 1024)
        row_count = len(df)
        column_count = len(df.columns)

        columns_info: List[ColumnSchema] = []

        for column in df.columns:
            data_type = str(df[column].dtype)
            sample_values = df[column].dropna().head(sample_rows).tolist()
            non_null_count = int(df[column].count())

            column_info: ColumnSchema = {
                "name": column,
                "description": "",
                "type": data_type,
                "sample_values": sample_values,
                "non_null_count": non_null_count,
            }
            columns_info.append(column_info)

        dataset_schema: DatasetSchema = {
            "name": matching_files[0],
            "file_path": file_path,
            "file_size_mb": round(file_size, 2),
            "row_count": row_count,
            "column_count": column_count,
            "columns": columns_info,
        }

        return dataset_schema

    except Exception as e:
        raise ValueError(f"Error getting dataset preview: {str(e)}")
