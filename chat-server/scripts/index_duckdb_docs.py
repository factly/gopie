import asyncio
import json
import sys
from pathlib import Path

from langchain_core.documents import Document

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings  # noqa: E402
from app.services.qdrant.qdrant_setup import QdrantSetup  # noqa: E402
from app.utils.model_registry.model_provider import (  # noqa: E402
    get_model_provider,
)

MIN_CONTENT_LENGTH = 50


async def index_duckdb_docs():
    print("📚 Indexing DuckDB Documentation into Qdrant")

    scraped_file = Path(__file__).parent / "data" / "duckdb_docs_raw.json"
    if not scraped_file.exists():
        print(f"No scraped data found at {scraped_file}")
        print("Please run: python3 scripts/scrape_duckdb_docs.py first")
        return

    print(f"Loading scraped content from {scraped_file}")
    with open(scraped_file, "r", encoding="utf-8") as f:
        scraped_data = json.load(f)

    embeddings = get_model_provider().get_embeddings_model()
    async_client = None

    try:
        print("🗑️  Clearing existing collection...")
        async_client = await QdrantSetup.get_async_client(settings.QDRANT_DUCKDB_COLLECTION)

        collections = (await async_client.get_collections()).collections
        collection_names = [c.name for c in collections]

        if settings.QDRANT_DUCKDB_COLLECTION in collection_names:
            await async_client.delete_collection(settings.QDRANT_DUCKDB_COLLECTION)
            print("   Deleted existing collection")

        config = QdrantSetup.get_qdrant_config(settings.QDRANT_DUCKDB_COLLECTION)
        await async_client.create_collection(**config)
        print("   Created fresh collection")

        vector_store = QdrantSetup.get_vector_store(
            embeddings, collection_name=settings.QDRANT_DUCKDB_COLLECTION
        )

        documents = []
        for item in scraped_data:
            page_content = item.get("content", "")

            if not page_content.strip() or len(page_content.strip()) < MIN_CONTENT_LENGTH:
                continue
            metadata = {
                "source": "duckdb_docs",
            }

            documents.append(Document(page_content=page_content, metadata=metadata))

        print(f"Prepared {len(documents)} documents for indexing")
        await vector_store.aadd_documents(documents)
        print("✅ Successfully indexed DuckDB documentation")
        print(f"   Total documents: {len(documents)}")

    except Exception as e:
        print(f"❌ Error during indexing: {e}")
        raise
    finally:
        await QdrantSetup.close_clients()


if __name__ == "__main__":
    asyncio.run(index_duckdb_docs())
