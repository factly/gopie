import logging
import os
from typing import Any

import duckdb


def generate_schema(dataset_name: str) -> tuple[Any, Any]:
    data_dir = "data"
    file_path = os.path.join(data_dir, f"{dataset_name}.csv")

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File {file_path} does not exist")

    conn = duckdb.connect()
    conn.execute(
        f'CREATE TABLE "{dataset_name}" AS SELECT * FROM "{file_path}"'
    )

    result = conn.sql(f"SUMMARIZE {dataset_name}").fetchdf()
    logging.info(f"Raw SUMMARIZE result: {result}")

    sample_values_query = f"SELECT * FROM {dataset_name} LIMIT 5"
    sample_data = conn.sql(sample_values_query).fetchdf()

    conn.close()
    return result, sample_data
