import os
from typing import List

import pandas as pd

from src.lib.graph.types import ColumnSchema, DatasetSchema
from src.utils.col_desc_generator import generate_column_descriptions

DATA_DIR = "./data"


def get_dataset_preview(dataset_name: str, sample_rows: int = 3) -> DatasetSchema:
    """
    Get metadata and sample data from a dataset.

    Args:
        dataset_name: Name of the dataset to find in the data directory
        sample_rows: Number of sample rows to include in the preview
        add_constraints: Whether to add SQL constraints through profiling

    Returns:
        A DatasetSchema object containing metadata and schema information
    """
    try:
        try:
            from src.utils.dataset_profiling import get_profiled_dataset

            for suffix in [".csv", ""]:
                cached_dataset = get_profiled_dataset(f"{dataset_name}{suffix}")
                if cached_dataset:
                    print(f"Using pre-profiled dataset from cache: {dataset_name}")
                    return cached_dataset
        except Exception as e:
            print(f"Warning: Could not retrieve pre-profiled dataset: {e}")

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
            sample_values = (
                df[column].dropna().drop_duplicates().head(sample_rows).tolist()
            )
            non_null_count = int(df[column].count())

            column_info: ColumnSchema = {
                "name": column,
                "description": "",
                "type": data_type,
                "sample_values": sample_values,
                "non_null_count": non_null_count,
                "constraints": {},
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

        try:
            column_descriptions = generate_column_descriptions(dataset_schema)

            for column in dataset_schema["columns"]:
                if column["name"] in column_descriptions:
                    column["description"] = column_descriptions[column["name"]]
                else:
                    column["description"] = (
                        f"Column representing {column['name'].replace('_', ' ').lower()}"
                    )

        except Exception as e:
            print(f"Warning: Could not generate column descriptions: {e}")

        try:
            from src.utils.dataset_profiling import profile_dataset

            dataset_schema = profile_dataset(dataset_schema)
            print("Added column constraints through profiling")
        except Exception as e:
            print(f"Warning: Could not generate column constraints: {e}")

        return dataset_schema

    except Exception as e:
        raise ValueError(f"Error getting dataset preview: {str(e)}")
