import logging
from typing import List, Optional

from app.core.config import settings
from app.services.qdrant.qdrant_setup import (
    initialize_qdrant_client,
    setup_vector_store,
)
from app.services.qdrant.vector_store import (
    perform_similarity_search,
)
from app.utils.dataset_info import get_dataset_preview


def find_and_preview_dataset(
    query: str,
    top_k: int = settings.QDRANT_TOP_K,
    dataset_ids: Optional[List[str]] = None
):
    """
    Find relevant datasets based on a query and provide their previews.

    Args:
        query: The search query
        top_k: Number of results to return
        dataset_ids: Optional list of dataset IDs to filter results
    """
    client = initialize_qdrant_client()
    vector_store = setup_vector_store(client)

    results = perform_similarity_search(vector_store, query, top_k=top_k, dataset_ids=dataset_ids)

    previews = []
    for result in results:
        if "file_name" not in result.metadata or not result.metadata[
            "file_name"
        ].endswith(".csv"):
            logging.info(
                f"Skipping document without proper CSV metadata: {result.metadata.get('source', 'Unknown')}"
            )
            continue

        dataset_name = result.metadata["file_name"].replace(".csv", "")
        try:
            preview_data = get_dataset_preview(dataset_name)
            previews.append(
                {
                    "relevance_info": result,
                    "metadata": preview_data.get("metadata", {}),
                    "sample_data": preview_data.get("sample_data", []),
                }
            )
        except Exception as e:
            logging.info(f"Error getting preview for {dataset_name}: {e}")
            previews.append({"relevance_info": result, "error": str(e)})

    logging.info(f"Found {len(previews)} relevant datasets")
    return previews


def format_dataset_preview(result):
    """Format a dataset preview for display."""
    dataset = result["relevance_info"]
    output = []

    output.append(f"Dataset: {dataset.metadata.get('file_name', 'Unknown')}")
    output.append(f"Rows: {dataset.metadata.get('row_count', 'Unknown')}")

    if "error" in result:
        output.append(f"Error getting preview: {result['error']}")
    else:
        metadata = result.get("metadata", {})

        column_names = metadata.get("columns", [])
        if column_names:
            output.append(
                f"Columns: {', '.join(column_names[:5])}{'...' if len(column_names) > 5 else ''}"
            )

        column_types = metadata.get("column_types", {})
        if column_types:
            output.append("Column types:")
            for col, dtype in list(column_types.items())[:3]:
                output.append(f"  - {col}: {dtype}")
            if len(column_types) > 3:
                output.append("  - ...")

    output.append(f"Match details: {dataset.page_content[:150]}...")

    return "\n".join(output)
