from uuid import uuid4

from langchain_core.documents import Document
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

from src.lib.config.langchain_config import lc


def initialize_qdrant_client(url="http://localhost:6333"):
    """Initialize the Qdrant client and create a collection if it doesn't exist."""
    client = QdrantClient(url=url)

    collections = client.get_collections().collections
    collection_names = [collection.name for collection in collections]

    if "dataset_collection" not in collection_names:
        client.create_collection(
            collection_name="dataset_collection",
            vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
        )
    return client


def setup_vector_store(client, collection_name="dataset_collection"):
    """Set up a vector store using the provided client."""
    return QdrantVectorStore(
        client=client,
        collection_name=collection_name,
        embedding=lc.embeddings_model,
    )


def create_sample_documents():
    """Create sample documents for demonstration."""
    document_1 = Document(
        page_content="I had chocalate chip pancakes and scrambled eggs for breakfast this morning.",
        metadata={"source": "tweet"},
    )

    document_2 = Document(
        page_content="The weather forecast for tomorrow is cloudy and overcast, with a high of 62 degrees.",
        metadata={"source": "news"},
    )

    documents = [document_1, document_2]
    uuids = [str(uuid4()) for _ in range(len(documents))]

    return documents, uuids


def add_documents_to_vector_store(vector_store, documents, ids=None):
    """Add documents to the vector store."""
    if ids is None:
        ids = [str(uuid4()) for _ in range(len(documents))]
    vector_store.add_documents(documents=documents, ids=ids)


def perform_similarity_search(vector_store, query, top_k=1):
    """Perform a similarity search."""
    return vector_store.similarity_search(query, k=top_k)


def test_embeddings():
    client = initialize_qdrant_client()
    vector_store = setup_vector_store(client)

    documents, uuids = create_sample_documents()
    add_documents_to_vector_store(vector_store, documents, uuids)

    result = perform_similarity_search(vector_store, "chocolate pancakes")
    print(result)
