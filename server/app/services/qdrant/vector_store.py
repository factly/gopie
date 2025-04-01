import logging
import os
from typing import Dict, List, Optional

import pandas as pd

from server.app.core.config import settings
from server.app.models.data import DatasetSchema, TableSchema
from server.app.services.qdrant.qdrant_setup import initialize_qdrant_client, setup_vector_store


def create_dataset_document(dataset_name: str, table: TableSchema) -> Dict:
    """
    Create a document for a dataset table.

    Args:
        dataset_name: Name of the dataset
        table: TableSchema for the table

    Returns:
        Document for the table with metadata
    """
    column_descriptions = []
    for column in table.columns:
        column_descriptions.append(f"- {column.name} ({column.type}): {column.description}")

    column_text = "\n".join(column_descriptions)

    document_text = f"""
        Dataset: {dataset_name}
        Table: {table.name}
Description: {table.description or f"Table with {table.row_count} rows"}
Rows: {table.row_count}
Columns:
{column_text}
    """.strip()

    metadata = {
        "dataset_name": dataset_name,
        "table_name": table.name,
        "row_count": table.row_count,
        "column_count": len(table.columns),
        "column_names": [col.name for col in table.columns],
    }

    return {
        "page_content": document_text,
        "metadata": metadata
    }


def vectorize_dataset(dataset_name: str, table: TableSchema) -> bool:
    """
    Vectorize a single dataset table and store in Qdrant.

    Args:
        dataset_name: Name of the dataset
        table: TableSchema for the table

    Returns:
        True if successful, False otherwise
    """
    try:
        client = initialize_qdrant_client()
        vector_store = setup_vector_store(client)

        document = create_dataset_document(dataset_name, table)

        vector_store.add_texts(
            texts=[document["page_content"]],
            metadatas=[document["metadata"]]
        )

        logging.info(f"Vectorized table {table.name} from dataset {dataset_name}")
        return True

    except Exception as e:
        logging.error(f"Error vectorizing dataset {dataset_name}, table {table.name}: {e}")
        return False


def vectorize_datasets(datasets: Dict[str, DatasetSchema]) -> int:
    """
    Vectorize all datasets and store in Qdrant.

    Args:
        datasets: Dictionary of dataset schemas

    Returns:
        Number of documents vectorized
    """
    try:
        client = initialize_qdrant_client()
        vector_store = setup_vector_store(client)

        documents = []

        for dataset_name, dataset in datasets.items():
            for table in dataset.tables:
                document = create_dataset_document(dataset_name, table)
                documents.append(document)

        if documents:
            vector_store.add_texts(
                texts=[doc["page_content"] for doc in documents],
                metadatas=[doc["metadata"] for doc in documents]
            )
            logging.info(f"Vectorized {len(documents)} dataset tables")

        return len(documents)

    except Exception as e:
        logging.error(f"Error vectorizing datasets: {e}")
        return 0


def find_relevant_datasets(query: str, top_k: int = 3) -> List[Dict]:
    """
    Find datasets relevant to a natural language query.

    Args:
        query: Natural language query
        top_k: Maximum number of results to return

    Returns:
        List of relevant dataset documents with scores
    """
    try:
        client = initialize_qdrant_client()
        vector_store = setup_vector_store(client)

        results = vector_store.similarity_search_with_score(query, k=top_k)

        formatted_results = []
        for doc, score in results:
            formatted_results.append({
                "dataset_name": doc.metadata["dataset_name"],
                "table_name": doc.metadata["table_name"],
                "columns": doc.metadata["column_names"],
                "row_count": doc.metadata["row_count"],
                "description": doc.page_content,
                "score": float(score),
            })

        return formatted_results

    except Exception as e:
        logging.error(f"Error finding relevant datasets: {e}")
        return []


def find_and_preview_dataset(query: str, top_k: int = 1, preview_rows: int = 5) -> Dict:
    """
    Find and preview data from a dataset relevant to a natural language query.

    Args:
        query: Natural language query
        top_k: Maximum number of results to return
        preview_rows: Number of rows to preview

    Returns:
        Dataset preview information
    """
    try:
        relevant_datasets = find_relevant_datasets(query, top_k=top_k)

        if not relevant_datasets:
            return {"error": "No relevant datasets found"}

        best_match = relevant_datasets[0]
        dataset_name = best_match["dataset_name"]
        table_name = best_match["table_name"]

        data_dir = settings.DATA_DIR
        dataset_path = os.path.join(data_dir, dataset_name)

        supported_extensions = ['.csv', '.parquet', '.json']
        file_path = None

        for ext in supported_extensions:
            possible_path = os.path.join(dataset_path, f"{table_name}{ext}")
            if os.path.exists(possible_path):
                file_path = possible_path
                break

        if not file_path:
            return {
                "error": f"Table {table_name} not found in dataset {dataset_name}",
                "matches": relevant_datasets
            }

        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        elif file_path.endswith('.parquet'):
            df = pd.read_parquet(file_path)
        elif file_path.endswith('.json'):
            df = pd.read_json(file_path)
        else:
            return {
                "error": f"Unsupported file format: {file_path}",
                "matches": relevant_datasets
            }

        preview_data = df.head(preview_rows).to_dict(orient='records')

        return {
            "dataset_name": dataset_name,
            "table_name": table_name,
            "columns": list(df.columns),
            "total_rows": len(df),
            "preview_rows": preview_rows,
            "preview_data": preview_data,
            "matches": relevant_datasets
        }

    except Exception as e:
        logging.error(f"Error previewing dataset: {e}")
        return {"error": str(e)}