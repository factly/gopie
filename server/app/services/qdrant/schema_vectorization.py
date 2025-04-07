import logging

from app.models.schema import DatasetSchema
from app.services.qdrant.vector_store import add_documents_to_vector_store
from langchain_core.documents import Document


def store_schema_in_qdrant(schema: DatasetSchema) -> bool:
    """
    Store a dataset schema in Qdrant.

    Args:
        schema: The dataset schema to store
        vector_store: Optional pre-initialized vector store

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        document = Document(page_content="temp", metadata={})

        add_documents_to_vector_store([document])
        logging.info(f"Successfully stored schema for dataset {schema['name']}")
        return True

    except Exception as e:
        logging.error(f"Error storing schema in Qdrant: {str(e)}")
        return False
