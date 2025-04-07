from typing import Any, Dict, List

from app.services.qdrant_client import initialize_qdrant_client
from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.get("/documents", response_model=List[Dict[str, Any]])
async def get_all_documents():
    """
    Retrieve all documents stored in Qdrant
    """
    try:
        client = initialize_qdrant_client()

        collections = client.get_collections().collections
        collection_names = [collection.name for collection in collections]

        all_documents = []

        for collection_name in collection_names:
            scroll_results = client.scroll(
                collection_name=collection_name,
                limit=1000,
            )

            documents = scroll_results[0]

            for doc in documents:
                document_data = {
                    "id": doc.id,
                    "collection": collection_name,
                    "payload": doc.payload,
                }
                all_documents.append(document_data)

        return all_documents

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving documents: {str(e)}"
        )
