import os
from typing import Dict, List, Tuple
from uuid import uuid4

import pandas as pd
from langchain_core.documents import Document

DATA_DIR = "./data"


def extract_csv_metadata(file_path: str) -> Dict:
    """Extract metadata from a CSV file."""
    try:
        df = pd.read_csv(file_path)

        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path) / (1024 * 1024)
        row_count = len(df)
        column_count = len(df.columns)

        columns_info = []
        for column in df.columns:
            data_type = str(df[column].dtype)
            sample_values = df[column].dropna().head(3).tolist()
            column_info = {
                "name": column,
                "type": data_type,
                "sample_values": sample_values,
            }
            columns_info.append(column_info)

        return {
            "file_name": file_name,
            "file_path": file_path,
            "file_size_mb": round(file_size, 2),
            "row_count": row_count,
            "column_count": column_count,
            "columns": columns_info,
        }
    except Exception as e:
        print(f"Error extracting metadata from {file_path}: {e}")
        return {
            "file_name": os.path.basename(file_path),
            "file_path": file_path,
            "error": str(e),
        }


def csv_metadata_to_document(metadata: Dict) -> Document:
    """Convert CSV metadata to a Document object for vectorization."""
    content_parts = [
        f"Dataset: {metadata['file_name']}",
        f"Rows: {metadata.get('row_count', 'Unknown')}",
        f"Columns: {metadata.get('column_count', 'Unknown')}",
    ]

    if "columns" in metadata:
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
            "file_name": metadata["file_name"],
            "file_size_mb": metadata.get("file_size_mb", "Unknown"),
            "row_count": metadata.get("row_count", "Unknown"),
            "column_count": metadata.get("column_count", "Unknown"),
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
