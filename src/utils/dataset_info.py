import os
from typing import Any, Dict

import pandas as pd
from src.tools.list_tables import get_data_directory

def get_dataset_preview(dataset_name: str, sample_rows: int = 3) -> Dict[str, Any]:
    """
    Get metadata and sample data from a dataset.

    Args:
        dataset_name: Name of the dataset (without .csv extension)
        sample_rows: Number of sample rows to return (default: 5)

    Returns:
        Dictionary containing dataset metadata and sample data
    """
    try:
        data_dir = get_data_directory()
        matching_files = [f for f in os.listdir(data_dir)
                        if f.endswith('.csv') and dataset_name.lower() in f.lower()]

        if not matching_files:
            raise FileNotFoundError(f"Dataset not found: {dataset_name}")

        file_path = os.path.join(data_dir, matching_files[0])
        df = pd.read_csv(file_path)

        # Get metadata
        metadata = {
            "name": matching_files[0],
            "total_rows": len(df),
            "columns": list(df.columns),
            "column_types": {col: str(df[col].dtype) for col in df.columns},
            "non_null_counts": {col: int(df[col].count()) for col in df.columns},
            "sample_values": {col: list(df[col].dropna().unique()[:5]) for col in df.columns}
        }

        # Get sample rows
        sample_data = df.head(sample_rows).to_dict('records')

        return {
            "metadata": metadata,
            "sample_data": sample_data
        }

    except Exception as e:
        raise ValueError(f"Error getting dataset preview: {str(e)}")
