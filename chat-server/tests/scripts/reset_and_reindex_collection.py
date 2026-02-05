"""
Qdrant Collection Migration Script

Migrates/Reindexes data from a source collection to a destination collection 
with hybrid vector support (dense + sparse).

Usage:
    python scripts/reset_and_reindex_collection.py --source old_coll --destination new_coll --dry-run
    python scripts/reset_and_reindex_collection.py --source old_coll --destination new_coll
"""

import argparse
import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

sys.path.insert(0, str(Path(__file__).parents[2]))

from qdrant_client import AsyncQdrantClient, models  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.log import custom_logger as logger  # noqa: E402
from app.services.qdrant.qdrant_setup import QdrantSetup  # noqa: E402
from app.services.qdrant.vector_store import (  # noqa: E402
    SparseModelManager,
    generate_sparse_vector,
)

DEFAULT_BATCH_SIZE = 100
CLIENT_TIMEOUT = 60
SEPARATOR = "=" * 60


@dataclass
class MigrationStats:
    total_read: int = 0
    total_uploaded: int = 0
    total_failed: int = 0
    dry_run: bool = False


def extract_dense_vector(point: models.Record) -> list[float]:
    """Extract dense vector from a point, handling old and new formats."""
    vectors = point.vector

    if vectors is None:
        raise ValueError(f"Point {point.id} has no vectors")

    if isinstance(vectors, dict):
        if "dense" in vectors:
            dense = vectors["dense"]
            if isinstance(dense, list):
                return cast(list[float], dense)
            raise ValueError(f"Point {point.id} has invalid dense vector type: {type(dense)}")

        if "sparse" not in vectors and vectors:
            first_value = next(iter(vectors.values()))
            if isinstance(first_value, list):
                return cast(list[float], first_value)
            raise ValueError(f"Point {point.id} has invalid vector type: {type(first_value)}")

        raise ValueError(f"Point {point.id} has no dense vector in dict: {list(vectors.keys())}")

    if isinstance(vectors, list):
        return cast(list[float], vectors)

    raise ValueError(f"Point {point.id} has unexpected vector format: {type(vectors)}")


def build_sparse_text(metadata: dict[str, Any]) -> str:
    dataset_name = metadata.get("dataset_name", "")
    name = metadata.get("name", "")
    description = metadata.get("dataset_description", "")
    return f"{dataset_name} {name} {description}".strip()


def run_generate_sparse_vector(text: str) -> models.SparseVector:
    """Wrapper to run synchronous sparse vector generation."""
    try:
        return generate_sparse_vector(text)
    except Exception as e:
        logger.error(f"Error generating sparse vector for text '{text[:50]}...': {e}")
        # Return empty sparse vector as fallback or raise?
        # For now, let's propagate error to handle it at point level
        raise e


async def process_point(point: models.Record) -> models.PointStruct:
    """Transform a point into a hybrid point asynchronously."""
    payload = point.payload or {}
    metadata = payload.get("metadata", {})

    dense_vector = extract_dense_vector(point)
    sparse_text = build_sparse_text(metadata)

    # Run CPU-bound task in thread pool
    sparse_vector = await asyncio.to_thread(run_generate_sparse_vector, sparse_text)

    return models.PointStruct(
        id=point.id,
        vector={"dense": dense_vector, "sparse": sparse_vector},
        payload=payload,
    )


async def process_and_upload_batch(
    client: AsyncQdrantClient,
    collection_name: str,
    points: list[models.Record],
    stats: MigrationStats,
) -> None:
    """Process a batch of points and upload them to the destination."""
    if not points:
        return

    transformed_points: list[models.PointStruct] = []

    # Process points concurrently
    tasks = [process_point(p) for p in points]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for i, res in enumerate(results):
        if isinstance(res, Exception):
            logger.error(f"Failed to process point {points[i].id}: {res}")
            stats.total_failed += 1
        else:
            transformed_points.append(res)

    if not transformed_points:
        return

    if stats.dry_run:
        logger.info(f"  [DRY RUN] Would upload {len(transformed_points)} points")
        stats.total_uploaded += len(transformed_points)
        return

    try:
        await client.upsert(
            collection_name=collection_name,
            points=transformed_points,
        )
        stats.total_uploaded += len(transformed_points)
        input_count = len(points)
        success_count = len(transformed_points)
        logger.info(f"  Uploaded batch: {success_count}/{input_count} successful")
    except Exception as e:
        logger.error(f"  Batch upload failed: {e}")
        stats.total_failed += len(transformed_points)


async def migrate_collection(
    source_collection: str,
    dest_collection: str,
    batch_size: int,
    dry_run: bool,
    host: str,
    port: int,
) -> MigrationStats:
    """Main migration logic."""

    # Initialize client with gRPC for better performance
    client = AsyncQdrantClient(
        host=host,
        grpc_port=port,  # Standard Qdrant gRPC port (6333 is HTTP)
        prefer_grpc=True,
        timeout=CLIENT_TIMEOUT,
    )

    stats = MigrationStats(dry_run=dry_run)

    try:
        # Check source
        logger.info(f"Checking source collection: {source_collection}")
        if not await client.collection_exists(source_collection):
            logger.error(f"Source collection '{source_collection}' not found!")
            return stats

        # Prepare destination
        logger.info(f"Preparing destination collection: {dest_collection}")
        if not dry_run:
            # Use QdrantSetup to ensure destination exists with correct config
            # We call get_async_client to trigger creation logic if needed
            await QdrantSetup.get_async_client(dest_collection)
        else:
            if not await client.collection_exists(dest_collection):
                logger.info(f"  [DRY RUN] Would create destination collection '{dest_collection}'")

        # Start migration
        logger.info(f"Starting migration from '{source_collection}' to '{dest_collection}'")
        logger.info(f"Batch size: {batch_size}")

        offset = None
        while True:
            # Scroll source collection
            points_batch, next_offset = await client.scroll(
                collection_name=source_collection,
                limit=batch_size,
                offset=offset,
                with_payload=True,
                with_vectors=True,
            )

            if not points_batch:
                break

            stats.total_read += len(points_batch)

            await process_and_upload_batch(client, dest_collection, points_batch, stats)

            if next_offset is None:
                break
            offset = next_offset

    except Exception as e:
        logger.exception(f"Migration error: {e}")
    finally:
        await client.close()
        await QdrantSetup.close_clients()

    return stats


def print_summary(stats: MigrationStats) -> None:
    logger.info(SEPARATOR)
    logger.info("Migration Summary")
    logger.info(SEPARATOR)
    logger.info(f"Total Read     : {stats.total_read}")
    logger.info(f"Total Uploaded : {stats.total_uploaded}")
    logger.info(f"Total Failed   : {stats.total_failed}")
    if stats.dry_run:
        logger.info("[DRY RUN] No changes were applied.")
    logger.info(SEPARATOR)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Migrate Qdrant collection with hybrid vector re-indexing",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--source",
        required=True,
        help="Name of the source collection",
    )

    parser.add_argument(
        "--host",
        required=True,
        help="Host of the Qdrant instance",
    )
    parser.add_argument(
        "--port",
        required=True,
        help="GRPC Port of the Qdrant instance",
    )
    parser.add_argument(
        "--destination",
        required=True,
        help="Name of the destination collection",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate migration without writing to destination",
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help="Number of points to process per batch",
    )

    return parser.parse_args()


async def main() -> None:
    args = parse_args()

    logger.info(SEPARATOR)
    logger.info("Qdrant Migration Tool")
    logger.info(f"Source      : {args.source}")
    logger.info(f"Destination : {args.destination}")
    logger.info(f"Dry Run     : {args.dry_run}")
    logger.info(SEPARATOR)

    # Initialize sparse model SYNCHRONOUSLY before any async operations
    # This prevents race conditions when multiple threads try to download the model
    logger.info("Initializing sparse vector model...")
    try:
        SparseModelManager.get_model()
        logger.info("Sparse vector model initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize sparse model: {e}")
        raise

    stats = await migrate_collection(
        source_collection=args.source,
        dest_collection=args.destination,
        batch_size=args.batch_size,
        dry_run=args.dry_run,
        host=args.host,
        port=args.port,
    )

    print_summary(stats)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("Migration interrupted by user.")
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        sys.exit(1)
