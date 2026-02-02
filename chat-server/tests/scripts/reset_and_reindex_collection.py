"""
Qdrant Collection Reset & Reindex Script

Migrates a Qdrant collection to support hybrid search (dense + sparse vectors).

Usage:
    python scripts/reset_and_reindex_collection.py --dry-run
    python scripts/reset_and_reindex_collection.py
    python scripts/reset_and_reindex_collection.py --batch-size 50
"""

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

sys.path.insert(0, str(Path(__file__).parent.parent))

from qdrant_client import QdrantClient, models  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.log import custom_logger as logger  # noqa: E402
from app.services.qdrant.qdrant_setup import QdrantSetup  # noqa: E402
from app.services.qdrant.vector_store import (  # noqa: E402
    generate_sparse_vector,
)

DEFAULT_BATCH_SIZE = 100
SCROLL_BATCH_SIZE = 100
CLIENT_TIMEOUT = 60
SEPARATOR = "=" * 60


@dataclass
class MigrationResult:
    """Results from the migration process."""

    total_exported: int
    success_count: int
    failed_count: int
    dry_run: bool

    @property
    def success_rate(self) -> float:
        if self.total_exported == 0:
            return 100.0
        return (self.success_count / self.total_exported) * 100


@dataclass
class CollectionStatus:
    """Status of a Qdrant collection."""

    name: str
    exists: bool
    points_count: int = 0
    has_dense: bool = False
    has_sparse: bool = False

    @property
    def is_hybrid_ready(self) -> bool:
        return self.has_dense and self.has_sparse


def get_qdrant_client() -> QdrantClient:
    return QdrantClient(
        url=f"http://{settings.QDRANT_HOST}:{settings.QDRANT_PORT}",
        timeout=CLIENT_TIMEOUT,
    )


def collection_exists(client: QdrantClient, collection_name: str) -> bool:
    collections = [c.name for c in client.get_collections().collections]
    return collection_name in collections


def get_collection_status(client: QdrantClient, collection_name: str) -> CollectionStatus:
    if not collection_exists(client, collection_name):
        return CollectionStatus(name=collection_name, exists=False)

    try:
        info = client.get_collection(collection_name)
        vectors_config = info.config.params.vectors
        sparse_config = info.config.params.sparse_vectors

        has_dense = "dense" in vectors_config if isinstance(vectors_config, dict) else True
        has_sparse = sparse_config is not None and "sparse" in sparse_config

        return CollectionStatus(
            name=collection_name,
            exists=True,
            points_count=info.points_count or 0,
            has_dense=has_dense,
            has_sparse=has_sparse,
        )
    except Exception as e:
        logger.error(f"Failed to get collection status: {e}")
        return CollectionStatus(name=collection_name, exists=True)


def export_all_points(client: QdrantClient, collection_name: str) -> list[models.Record]:
    """Export all points from the Qdrant collection."""
    if not collection_exists(client, collection_name):
        logger.warning(f"Collection '{collection_name}' does not exist. Nothing to export.")
        return []

    logger.info(f"Exporting points from '{collection_name}'...")

    all_points: list[models.Record] = []
    offset = None

    while True:
        points, next_offset = client.scroll(
            collection_name=collection_name,
            limit=SCROLL_BATCH_SIZE,
            offset=offset,
            with_payload=True,
            with_vectors=True,
        )

        if not points:
            break

        all_points.extend(points)
        logger.info(f"  Exported {len(all_points)} points...")

        if next_offset is None:
            break

        offset = next_offset

    logger.info(f"Export complete: {len(all_points)} points")
    return all_points


def delete_collection(client: QdrantClient, collection_name: str) -> bool:
    """Delete a Qdrant collection. Returns True if deleted."""
    if not collection_exists(client, collection_name):
        logger.info(f"Collection '{collection_name}' does not exist, skipping delete.")
        return False

    logger.info(f"Deleting collection '{collection_name}'...")
    client.delete_collection(collection_name=collection_name)
    logger.info("Collection deleted.")
    return True


def create_hybrid_collection(collection_name: str) -> None:
    """Create a new collection with hybrid vector support."""
    logger.info(f"Creating collection '{collection_name}' with hybrid support...")
    QdrantSetup.get_sync_client(collection_name)
    logger.info("Collection created.")


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


def create_hybrid_point(point: models.Record) -> models.PointStruct:
    """Create a new point with both dense and sparse vectors."""
    payload = point.payload or {}
    metadata = payload.get("metadata", {})

    dense_vector = extract_dense_vector(point)
    sparse_text = build_sparse_text(metadata)
    sparse_vector = generate_sparse_vector(sparse_text)

    return models.PointStruct(
        id=point.id,
        vector={"dense": dense_vector, "sparse": sparse_vector},
        payload=payload,
    )


def upload_points_batch(
    client: QdrantClient,
    collection_name: str,
    points: list[models.Record],
    batch_num: int,
    total_batches: int,
    dry_run: bool = False,
) -> tuple[int, int]:
    """Process and upload a single batch. Returns (success_count, failed_count)."""
    success = 0
    failed = 0
    updated_points: list[models.PointStruct] = []

    for point in points:
        try:
            updated_points.append(create_hybrid_point(point))
        except Exception as e:
            metadata = point.payload.get("metadata", {}) if point.payload else {}
            dataset_id = metadata.get("dataset_id", "unknown")
            logger.error(f"Failed to process point {point.id} (dataset: {dataset_id}): {e}")
            failed += 1

    if dry_run:
        logger.info(f"  [DRY RUN] Batch {batch_num}/{total_batches}: {len(updated_points)} points")
        return len(updated_points), failed

    if updated_points:
        try:
            client.upsert(collection_name=collection_name, points=updated_points)
            success = len(updated_points)
            logger.info(f"  Batch {batch_num}/{total_batches}: {success} points uploaded")
        except Exception as e:
            logger.error(f"  Batch {batch_num}/{total_batches} failed: {e}")
            failed += len(updated_points)

    return success, failed


def upload_all_points(
    client: QdrantClient,
    collection_name: str,
    points: list[models.Record],
    batch_size: int = DEFAULT_BATCH_SIZE,
    dry_run: bool = False,
) -> tuple[int, int]:
    """Upload all points with regenerated sparse vectors."""
    if not points:
        logger.info("No points to upload.")
        return 0, 0

    total_batches = (len(points) + batch_size - 1) // batch_size
    mode = "DRY RUN" if dry_run else "UPLOADING"
    logger.info(f"{mode}: {len(points)} points in {total_batches} batches...")

    total_success = 0
    total_failed = 0

    for i in range(0, len(points), batch_size):
        batch = points[i : i + batch_size]
        batch_num = (i // batch_size) + 1

        success, failed = upload_points_batch(
            client=client,
            collection_name=collection_name,
            points=batch,
            batch_num=batch_num,
            total_batches=total_batches,
            dry_run=dry_run,
        )

        total_success += success
        total_failed += failed

    return total_success, total_failed


def print_header(collection_name: str, dry_run: bool) -> None:
    logger.info(SEPARATOR)
    logger.info("Qdrant Collection Reset & Reindex")
    logger.info(SEPARATOR)
    logger.info(f"Collection : {collection_name}")
    logger.info(f"Mode       : {'DRY RUN (no changes)' if dry_run else 'LIVE'}")
    logger.info(f"Qdrant     : {settings.QDRANT_HOST}:{settings.QDRANT_PORT}")
    logger.info(SEPARATOR)


def print_step(step: int, total: int, message: str) -> None:
    logger.info(f"\n[Step {step}/{total}] {message}")


def print_result(result: MigrationResult) -> None:
    logger.info(f"\n{SEPARATOR}")
    logger.info("Migration Summary")
    logger.info(SEPARATOR)
    logger.info(f"Total Exported : {result.total_exported}")
    logger.info(f"Uploaded       : {result.success_count}")
    logger.info(f"Failed         : {result.failed_count}")
    logger.info(f"Success Rate   : {result.success_rate:.1f}%")

    if result.dry_run:
        logger.info(f"\n{'*' * 40}")
        logger.info("DRY RUN - No changes were made.")
        logger.info("Run without --dry-run to execute.")
        logger.info("*" * 40)

    logger.info(SEPARATOR)


def print_collection_status(status: CollectionStatus) -> None:
    logger.info(f"\n{SEPARATOR}")
    logger.info("Collection Status")
    logger.info(SEPARATOR)
    logger.info(f"Name         : {status.name}")
    logger.info(f"Points       : {status.points_count}")
    logger.info(f"Dense Vectors: {'Yes' if status.has_dense else 'No'}")
    logger.info(f"Sparse Vectors: {'Yes' if status.has_sparse else 'No'}")
    logger.info(f"Hybrid Ready : {'Yes' if status.is_hybrid_ready else 'No'}")
    logger.info(SEPARATOR)


def run_migration(collection_name: str, batch_size: int, dry_run: bool) -> MigrationResult:
    """Execute the full migration process."""
    client = get_qdrant_client()

    print_step(1, 4, "Exporting existing data")
    exported_points = export_all_points(client, collection_name)

    if not exported_points:
        logger.warning("No data found. Creating empty hybrid collection.")

    print_step(2, 4, "Deleting old collection")
    if dry_run:
        logger.info("[DRY RUN] Would delete collection")
    else:
        delete_collection(client, collection_name)

    print_step(3, 4, "Creating hybrid collection")
    if dry_run:
        logger.info("[DRY RUN] Would create hybrid collection")
    else:
        create_hybrid_collection(collection_name)
        client = get_qdrant_client()

    print_step(4, 4, "Uploading with sparse vectors")
    success_count, failed_count = upload_all_points(
        client=client,
        collection_name=collection_name,
        points=exported_points,
        batch_size=batch_size,
        dry_run=dry_run,
    )

    if not dry_run and exported_points:
        status = get_collection_status(client, collection_name)
        print_collection_status(status)

        if not status.is_hybrid_ready:
            logger.error("Collection is NOT properly configured for hybrid search!")

    return MigrationResult(
        total_exported=len(exported_points),
        success_count=success_count,
        failed_count=failed_count,
        dry_run=dry_run,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reset Qdrant collection and reindex with hybrid vector support",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --dry-run          Preview changes without modifying anything
  %(prog)s                    Execute the migration
  %(prog)s --batch-size 50    Use smaller batches for large collections
        """,
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without making any modifications",
    )

    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        metavar="N",
        help=f"Points per upload batch (default: {DEFAULT_BATCH_SIZE})",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()
    collection_name = settings.QDRANT_COLLECTION

    print_header(collection_name, args.dry_run)

    try:
        result = run_migration(
            collection_name=collection_name,
            batch_size=args.batch_size,
            dry_run=args.dry_run,
        )
        print_result(result)

        return 0 if result.failed_count == 0 else 1

    except KeyboardInterrupt:
        logger.warning("\nMigration interrupted by user.")
        return 130

    except Exception as e:
        logger.exception(f"Migration failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
