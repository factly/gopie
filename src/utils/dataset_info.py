import os
from typing import Any, Dict

import pandas as pd

DATA_DIR = "./data"


def get_dataset_preview(dataset_name: str, sample_rows: int = 3) -> Dict[str, Any]:
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

        metadata = {
            "name": matching_files[0],
            "total_rows": len(df),
            "columns": list(df.columns),
            "column_types": {col: str(df[col].dtype) for col in df.columns},
            "non_null_counts": {col: int(df[col].count()) for col in df.columns},
            "sample_values": {
                col: list(df[col].dropna().unique()[:5]) for col in df.columns
            },
        }

        sample_data = df.head(sample_rows).to_dict("records")
        return {"metadata": metadata, "sample_data": sample_data}

    except Exception as e:
        raise ValueError(f"Error getting dataset preview: {str(e)}")
