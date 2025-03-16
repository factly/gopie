from src.utils.dataset_info import get_dataset_preview
from src.utils.qdrant.qdrant_setup import initialize_qdrant_client, setup_vector_store
from src.utils.qdrant.vector_store import perform_similarity_search, vectorize_datasets

DATA_DIR = "./data"


def filter_csv_documents(results):
    """Filter search results to include only CSV documents with proper metadata."""
    filtered_results = []
    for doc in results:
        if (
            "file_name" in doc.metadata
            and doc.metadata["file_name"].endswith(".csv")
            and "source" in doc.metadata
            and doc.metadata["source"].endswith(".csv")
        ):
            filtered_results.append(doc)

    return filtered_results


def find_relevant_datasets(vector_store, query: str, top_k: int = 3):
    """Find the most relevant datasets for a given query."""
    search_k = top_k * 2
    results = perform_similarity_search(vector_store, query, top_k=search_k)
    filtered_results = filter_csv_documents(results)

    if len(filtered_results) < top_k and len(filtered_results) < len(results):
        search_k = search_k * 2
        results = perform_similarity_search(vector_store, query, top_k=search_k)
        filtered_results = filter_csv_documents(results)

    return filtered_results[:top_k]


def find_and_preview_dataset(
    query: str, top_k: int = 3, directory_path: str = DATA_DIR
):
    """Find relevant datasets based on a query and provide their previews."""
    client = initialize_qdrant_client()
    vector_store = setup_vector_store(client)

    vector_store = vectorize_datasets(vector_store, directory_path)
    results = find_relevant_datasets(vector_store, query, top_k=top_k)

    previews = []
    for result in results:
        if "file_name" not in result.metadata or not result.metadata[
            "file_name"
        ].endswith(".csv"):
            print(
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
            print(f"Error getting preview for {dataset_name}: {e}")
            previews.append({"relevance_info": result, "error": str(e)})

    print(f"Found {len(previews)} relevant datasets")
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
