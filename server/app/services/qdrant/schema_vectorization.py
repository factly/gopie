import json
import logging
from typing import Any

from app.models.schema import DatasetSchema
from app.services.qdrant.vector_store import add_documents_to_vector_store
from langchain_core.documents import Document


def store_schema_in_qdrant(
    schema: Any, dataset_id: str, project_id: str, file_path: str
) -> bool:
    """
    Store a dataset schema in Qdrant.

    Args:
        schema (Any): The dataset schema to store.
        dataset_id (str): The unique identifier for the dataset.
        project_id (str): The unique identifier for the project.
        file_path (str): The file path of the dataset.

    Returns:
        bool: True if successful, False otherwise.
    """
    try:
        dataset_name = file_path.split("/")[-1]

        columns_details = []
        if schema.get("samples") and len(schema["samples"]) > 0:
            sample_data = schema["samples"][0].get("data", {})
            variables = schema.get("variables", {})

            for column_name, column_values in sample_data.items():
                sample_values = list(column_values.values())[:5]
                non_null_count = sum(1 for v in column_values.values() if v is not None)
                columns_details.append(
                    {
                        "name": column_name,
                        "description": f"Column containing {column_name} data",
                        "type": variables.get(column_name, {}).get("type", "string"),
                        "sample_values": sample_values,
                        "non_null_count": non_null_count,
                        "stats": variables.get(column_name, {}),
                    }
                )

        formatted_schema: DatasetSchema = {
            "name": dataset_name,
            "dataset_id": dataset_id,
            "file_path": file_path,
            "project_id": project_id,
            "analysis": schema["analysis"],
            "row_count": schema["table"]["n"],
            "col_count": schema["table"]["n_var"],
            "columns": schema["columns"],
            "columns_details": columns_details,
            "alerts": schema["alerts"],
            "duplicates": schema["duplicates"],
            "correlations": schema["correlations"],
            "missing_values": schema["missing_values"],
        }

        document = Document(
            page_content=json.dumps(formatted_schema, indent=2),
            metadata={
                "name": dataset_name,
                "dataset_id": dataset_id,
                "project_id": project_id,
                "schema": formatted_schema,
            },
        )

        add_documents_to_vector_store([document])
        logging.info(f"Successfully stored schema for dataset {dataset_name}")
        return True

    except Exception as e:
        logging.error(f"Error storing schema in Qdrant: {str(e)}")
        return False
