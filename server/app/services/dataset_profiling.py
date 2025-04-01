import os
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from server.app.workflow.graph.types import DatasetSchema


def analyze_column_constraints(df: pd.DataFrame, column_name: str) -> Dict[str, Any]:
    constraints = {}
    series = df[column_name]

    non_null_count = int(series.count())
    null_count = len(series) - non_null_count
    null_ratio = null_count / len(series) if len(series) > 0 else 0

    if null_ratio == 0:
        constraints["NOT_NULL"] = True

    if non_null_count == 0:
        constraints["empty"] = True
        return constraints

    unique_count = series.nunique()

    if unique_count == non_null_count and null_ratio == 0:
        constraints["PRIMARY_KEY"] = True
    elif unique_count == non_null_count:
        constraints["UNIQUE"] = True

    col_lower = column_name.lower()
    fk_patterns = ["_id", "id_", "_key", "_code", "_fk", "fk_", "_ref", "ref_"]

    is_potential_fk = False
    for pattern in fk_patterns:
        if pattern in col_lower:
            is_potential_fk = True
            break

    table_reference = None
    if "_id" in col_lower:
        potential_table = col_lower.split("_id")[0]
        if potential_table and len(potential_table) > 2:
            table_reference = potential_table
            is_potential_fk = True

    if is_potential_fk:
        constraints["FOREIGN_KEY"] = True
        if table_reference:
            constraints["references"] = table_reference

    if pd.api.types.is_numeric_dtype(series):
        non_null_series = series.dropna()
        if len(non_null_series) > 0:
            min_val = float(non_null_series.min())
            max_val = float(non_null_series.max())

            constraints["min"] = min_val
            constraints["max"] = max_val

            if min_val >= 0:
                constraints["CHECK"] = "positive"

            if pd.api.types.is_integer_dtype(series) or (
                pd.api.types.is_float_dtype(series)
                and all(
                    np.floor(x) == x
                    for x in non_null_series.iloc[: min(1000, len(non_null_series))]
                )
            ):
                constraints["TYPE"] = "integer"

            unique_values = non_null_series.unique()
            if len(unique_values) <= 2 and set(unique_values).issubset(
                {0, 1, 0.0, 1.0}
            ):
                constraints["TYPE"] = "boolean"

            if min_val >= 1900 and max_val <= 2100:
                constraints["TYPE"] = "year"

    elif pd.api.types.is_string_dtype(series) or pd.api.types.is_object_dtype(series):
        non_null_series = series.dropna().astype(str)
        if len(non_null_series) > 0:
            unique_ratio = unique_count / non_null_count

            if unique_ratio < 0.1 and unique_count <= 50:
                constraints["TYPE"] = "categorical"
                constraints["categories"] = (
                    non_null_series.value_counts().head(5).index.tolist()
                )

            value_counts = non_null_series.value_counts()
            if not value_counts.empty:
                most_common = value_counts.index[0]
                most_common_freq = value_counts.iloc[0] / non_null_count
                if most_common_freq > 0.9:
                    constraints["DEFAULT"] = str(most_common)

            sample_values = non_null_series.iloc[
                : min(100, len(non_null_series))
            ].tolist()

            if any(
                "@" in str(x) and "." in str(x).split("@")[-1]
                for x in sample_values[:20]
            ):
                constraints["TYPE"] = "email"

            if any(
                str(x).startswith(("http://", "https://")) for x in sample_values[:20]
            ):
                constraints["TYPE"] = "url"

    elif pd.api.types.is_datetime64_dtype(series):
        constraints["TYPE"] = "datetime"

    return constraints


def profile_dataset(dataset_schema: DatasetSchema) -> DatasetSchema:
    file_path = dataset_schema["file_path"]

    try:
        if dataset_schema["row_count"] > 1000000:
            constraints_by_column = {
                col["name"]: {} for col in dataset_schema["columns"]
            }

            chunk_size = 100000
            chunks_processed = 0

            for chunk in pd.read_csv(file_path, chunksize=chunk_size):
                chunks_processed += 1

                for column_name in chunk.columns:
                    chunk_constraints = analyze_column_constraints(chunk, column_name)

                    if chunks_processed == 1:
                        constraints_by_column[column_name] = chunk_constraints
                    else:
                        if (
                            "min" in chunk_constraints
                            and "min" in constraints_by_column[column_name]
                        ):
                            constraints_by_column[column_name]["min"] = min(
                                constraints_by_column[column_name]["min"],
                                chunk_constraints["min"],
                            )

                        if (
                            "max" in chunk_constraints
                            and "max" in constraints_by_column[column_name]
                        ):
                            constraints_by_column[column_name]["max"] = max(
                                constraints_by_column[column_name]["max"],
                                chunk_constraints["max"],
                            )

                        if (
                            "null_ratio" in chunk_constraints
                            and "null_ratio" in constraints_by_column[column_name]
                        ):
                            constraints_by_column[column_name]["null_ratio"] = (
                                (
                                    constraints_by_column[column_name]["null_ratio"]
                                    * (chunks_processed - 1)
                                )
                                + chunk_constraints["null_ratio"]
                            ) / chunks_processed

                        if (
                            "UNIQUE" in constraints_by_column[column_name]
                            and "duplicate_ratio" in chunk_constraints
                        ):
                            if chunk_constraints["duplicate_ratio"] > 0:
                                constraints_by_column[column_name].pop("UNIQUE", None)
                                constraints_by_column[column_name].pop(
                                    "PRIMARY_KEY", None
                                )

                        if (
                            "null_ratio" in chunk_constraints
                            and chunk_constraints["null_ratio"] > 0
                        ):
                            constraints_by_column[column_name].pop("NOT_NULL", None)
                            constraints_by_column[column_name].pop("PRIMARY_KEY", None)
        else:
            df = pd.read_csv(file_path)
            constraints_by_column = {
                col["name"]: analyze_column_constraints(df, col["name"])
                for col in dataset_schema["columns"]
            }
    except Exception as e:
        print(f"Error during dataset profiling: {e}")
        return dataset_schema

    for column in dataset_schema["columns"]:
        column_name = column["name"]
        if column_name in constraints_by_column:
            column["constraints"] = constraints_by_column[column_name]

    return dataset_schema


def find_key_relationships(
    dataset_schemas: List[DatasetSchema],
) -> Dict[str, List[Dict[str, Any]]]:
    relationships = {}

    if len(dataset_schemas) < 2:
        return relationships

    primary_keys = {}
    for schema in dataset_schemas:
        dataset_name = schema["name"]
        primary_keys[dataset_name] = []

        for column in schema["columns"]:
            column_name = column["name"]
            constraints = column.get("constraints", {}) or {}

            is_primary = False

            if constraints.get("PRIMARY_KEY", False):
                is_primary = True
            elif constraints.get("UNIQUE", False) and constraints.get(
                "NOT_NULL", False
            ):
                is_primary = True

            if column_name.lower() in [
                "id",
                "key",
                "code",
            ] or column_name.lower().endswith("_id"):
                is_primary = True

            if is_primary:
                primary_keys[dataset_name].append(
                    {"column": column_name, "data_type": column.get("type", "unknown")}
                )

    for i, schema1 in enumerate(dataset_schemas):
        dataset1 = schema1["name"]

        for j, schema2 in enumerate(dataset_schemas):
            if i >= j:
                continue

            dataset2 = schema2["name"]
            dataset_pair = f"{dataset1}:{dataset2}"
            join_keys = []

            for col1 in schema1["columns"]:
                col1_name = col1["name"]
                col1_constraints = col1.get("constraints", {}) or {}

                references_table = col1_constraints.get("references")
                if (
                    col1_constraints.get("FOREIGN_KEY", False)
                    and references_table
                    and references_table in dataset2.lower()
                ):
                    for pk in primary_keys[dataset2]:
                        join_keys.append(
                            {
                                "left_column": col1_name,
                                "right_column": pk["column"],
                                "relationship_type": "many-to-one",
                                "sql_join": f"{dataset1} JOIN {dataset2} ON {dataset1}.{col1_name} = {dataset2}.{pk['column']}",
                            }
                        )

            for col2 in schema2["columns"]:
                col2_name = col2["name"]
                col2_constraints = col2.get("constraints", {}) or {}

                references_table = col2_constraints.get("references")
                if (
                    col2_constraints.get("FOREIGN_KEY", False)
                    and references_table
                    and references_table in dataset1.lower()
                ):
                    for pk in primary_keys[dataset1]:
                        join_keys.append(
                            {
                                "right_column": col2_name,
                                "left_column": pk["column"],
                                "relationship_type": "one-to-many",
                                "sql_join": f"{dataset1} JOIN {dataset2} ON {dataset1}.{pk['column']} = {dataset2}.{col2_name}",
                            }
                        )

            for col1 in schema1["columns"]:
                col1_name = col1["name"]

                for col2 in schema2["columns"]:
                    col2_name = col2["name"]

                    if any(
                        jk["left_column"] == col1_name
                        and jk["right_column"] == col2_name
                        for jk in join_keys
                    ):
                        continue

                    if col1_name.lower() == col2_name.lower():
                        col1_constraints = col1.get("constraints", {}) or {}
                        col2_constraints = col2.get("constraints", {}) or {}

                        relationship_type = "unknown"
                        col1_unique = col1_constraints.get(
                            "UNIQUE", False
                        ) or col1_constraints.get("PRIMARY_KEY", False)
                        col2_unique = col2_constraints.get(
                            "UNIQUE", False
                        ) or col2_constraints.get("PRIMARY_KEY", False)

                        if col1_unique and col2_unique:
                            relationship_type = "one-to-one"
                        elif col1_unique:
                            relationship_type = "one-to-many"
                        elif col2_unique:
                            relationship_type = "many-to-one"
                        else:
                            relationship_type = "many-to-many"

                        join_keys.append(
                            {
                                "left_column": col1_name,
                                "right_column": col2_name,
                                "relationship_type": relationship_type,
                                "sql_join": f"{dataset1} JOIN {dataset2} ON {dataset1}.{col1_name} = {dataset2}.{col2_name}",
                            }
                        )

            if join_keys:
                relationships[dataset_pair] = join_keys

    return relationships


_profiled_datasets = {}


def get_profiled_dataset(dataset_name: str) -> Optional[DatasetSchema]:
    global _profiled_datasets
    return _profiled_datasets.get(dataset_name)


def profile_all_datasets(data_dir: str = "./data") -> Dict[str, DatasetSchema]:
    global _profiled_datasets

    try:
        os.makedirs(data_dir, exist_ok=True)

        if not os.path.exists(data_dir):
            print(f"Data directory {data_dir} does not exist.")
            return {}

        csv_files = [f for f in os.listdir(data_dir) if f.endswith(".csv")]

        if not csv_files:
            print("No CSV files found in the data directory.")
            _profiled_datasets = {}
            return {}

        from server.app.utils.dataset_info import get_dataset_preview

        for csv_file in csv_files:
            dataset_name = csv_file.replace(".csv", "")
            print(f"Profiling dataset: {dataset_name}")

            try:
                dataset_schema = get_dataset_preview(dataset_name, sample_rows=5)
                _profiled_datasets[dataset_name] = dataset_schema
                print(f"Successfully profiled dataset: {dataset_name}")
            except Exception as e:
                print(f"Error profiling dataset {dataset_name}: {e}")

        print(f"Profiled {len(_profiled_datasets)} datasets successfully.")
        return _profiled_datasets

    except Exception as e:
        print(f"Error during dataset profiling: {e}")
        _profiled_datasets = {}
        return {}