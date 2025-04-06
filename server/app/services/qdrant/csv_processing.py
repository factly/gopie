import os
from typing import List, Tuple
from uuid import uuid4

import pandas as pd
from langchain_core.documents import Document

from app.models.types import ColumnSchema, DatasetSchema

DATA_DIR = "./data"


def extract_csv_metadata(file_path: str) -> DatasetSchema:
    """Extract metadata from a CSV file."""
    try:
        df = pd.read_csv(file_path)

        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path) / (1024 * 1024)
        row_count = len(df)
        column_count = len(df.columns)

        columns_info: List[ColumnSchema] = []

        for column in df.columns:
            data_type = str(df[column].dtype)
            sample_values = df[column].dropna().drop_duplicates().head(10).tolist()
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

        return {
            "name": file_name,
            "file_path": file_path,
            "file_size_mb": round(file_size, 2),
            "row_count": row_count,
            "column_count": column_count,
            "columns": columns_info,

        }
    except Exception as e:
        print(f"Error extracting metadata from {file_path}: {e}")
        return {
            "name": os.path.basename(file_path),
            "file_path": file_path,
            "file_size_mb": 0.0,
            "row_count": 0,
            "column_count": 0,
            "columns": [],
        }


def csv_metadata_to_document(metadata: DatasetSchema) -> Document:
    """Convert CSV metadata to a Document object for vectorization."""
    content_parts = [
        f"Dataset: {metadata['name']}",
        f"Rows: {metadata['row_count']}",
        f"Columns: {metadata['column_count']}",
    ]

    if "columns" in metadata and metadata["columns"]:
        content_parts.append("Columns:")
        for col in metadata["columns"]:
            sample_values = (
                ", ".join([str(val) for val in col["sample_values"]])
                if col["sample_values"]
                else "N/A"
            )
            content_parts.append(
                f"  - {col['name']} (Type: {col['type']}, Sample values: {sample_values})"
            )

    page_content = "\n".join(content_parts)

    return Document(
        page_content=page_content,
        metadata={
            "source": metadata["file_path"],
            "file_name": metadata["name"],
            "file_size_mb": metadata.get("file_size_mb", 0),
            "row_count": metadata["row_count"],
            "column_count": metadata["column_count"],
        },
    )


def process_csv_directory(
    directory_path: str = DATA_DIR,
) -> Tuple[List[Document], List[str]]:
    """Process all CSV files in a directory and convert them to documents with rich metadata."""
    documents = []
    ids = []

    try:
        for file in os.listdir(directory_path):
            if file.endswith(".csv"):
                file_path = os.path.join(directory_path, file)
                metadata = extract_csv_metadata(file_path)
                document = csv_metadata_to_document(metadata)
                documents.append(document)
                ids.append(str(uuid4()))
    except Exception as e:
        print(f"Error processing CSV directory {directory_path}: {e}")

    return documents, ids
