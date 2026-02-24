"""
Replicate Production Projects to Local Instance

This script replicates entire projects with all datasets from a production Gopie instance
to a local instance, or uploads CSV files from a local folder.

Usage:
    # Replicate from production
    python -m tests.scripts.replicate_prod_to_local \
      --prod-url http://localhost:8000 \
      --local-url http://localhost:8001 \
      --json-file path/to/projects.json

    # Replicate a specific project
    python -m tests.scripts.replicate_prod_to_local \\
      --prod-url http://localhost:8000 \\
      --local-url http://localhost:8001 \\
      --project-id b7711501-e8ee-4804-82dd-5fe5af817dcd

    # Upload CSV files from local folder
    python -m tests.scripts.replicate_prod_to_local \
      --local-url http://localhost:8001 \
      --csv-folder /path/to/csv/folder \
      --project-name "My Project"
"""

import argparse
import asyncio
import csv
import io
import json
import sys
from pathlib import Path
from typing import Any

import boto3

from app.core.session import SingletonAiohttp
from tests.e2e.utils.dataset_manager import (
    S3_ACCESS_KEY_ID,
    S3_ENDPOINT_URL,
    S3_SECRET_ACCESS_KEY,
    _get_gopie_headers,
    create_gopie_project,
    create_s3_bucket_if_not_exists,
    ingest_dataset_to_gopie,
    upload_and_ingest_datasets,
    upload_file_to_s3,
)


class ProdToLocalReplicator:
    """
    Replicate projects and datasets from production to local Gopie instance.

    This class leverages utilities from dataset_manager.py for consistent behavior:
    - _get_gopie_headers() - Standard headers for API requests
    - create_gopie_project() - Creates new projects in Gopie
    - create_s3_bucket_if_not_exists() - Ensures S3/MinIO bucket exists
    - upload_and_ingest_datasets() - Batch CSV upload and ingestion (CSV mode)
    - upload_file_to_s3() - Individual file uploads (replication mode)
    - ingest_dataset_to_gopie() - Dataset ingestion (replication mode)
    """

    def __init__(self, prod_url: str, local_url: str):
        """
        Initialize the replicator.

        Args:
            prod_url: Production Gopie API URL (can be empty string for CSV-only mode)
            local_url: Local Gopie API URL
        """
        self.prod_url = prod_url.rstrip("/")
        self.local_url = local_url.rstrip("/")

        self.headers = _get_gopie_headers()

        create_s3_bucket_if_not_exists()

        self.s3_client = boto3.client(
            "s3",
            endpoint_url=S3_ENDPOINT_URL,
            aws_access_key_id=S3_ACCESS_KEY_ID,
            aws_secret_access_key=S3_SECRET_ACCESS_KEY,
        )

        self.project_mapping = {}
        self.dataset_mapping = {}
        self.cloned_datasets = set()

    async def get_project_details(
        self, project_id: str, from_prod: bool = True
    ) -> dict[str, Any] | None:
        """Fetch project details from prod or local."""
        base_url = self.prod_url if from_prod else self.local_url
        url = f"{base_url}/v1/api/projects/{project_id}"

        try:
            session = SingletonAiohttp.get_aiohttp_client()
            async with session.get(url, headers=self.headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    print(f"   ✗ HTTP {response.status}: {error_text[:200]}")
                    return None

                result = await response.json()
                return result.get("data", result) if isinstance(result, dict) else None

        except Exception as e:
            print(f"   ⚠️  Error fetching project: {e}")
            return None

    async def fetch_datasets(self, project_id: str) -> list[dict[str, Any]]:
        """Fetch all datasets for a project from production."""
        url = f"{self.prod_url}/v1/api/projects/{project_id}/datasets"
        params = {"limit": 100, "page": 1}

        try:
            session = SingletonAiohttp.get_aiohttp_client()
            async with session.get(url, params=params, headers=self.headers) as response:
                response.raise_for_status()
                response_json = await response.json()

            data_list = (
                response_json
                if isinstance(response_json, list)
                else response_json.get("results", response_json.get("data", []))
            )

            datasets = []
            for data in data_list:
                if data.get("id") and data.get("name"):
                    datasets.append(
                        {
                            "dataset_id": data["id"],
                            "dataset_name": data["name"],
                            "alias": data.get("alias", data["name"]),
                            "description": data.get("description", ""),
                        }
                    )

            return datasets

        except Exception as e:
            print(f"   ✗ Error fetching datasets: {e}")
            return []

    async def get_dataset_table_name(
        self, project_id: str, dataset_id: str
    ) -> tuple[str | None, dict[str, Any] | None]:
        """Fetch dataset details including table name."""
        url = f"{self.prod_url}/v1/api/projects/{project_id}/datasets/{dataset_id}"

        try:
            session = SingletonAiohttp.get_aiohttp_client()
            async with session.get(url, headers=self.headers) as response:
                if response.status != 200:
                    return None, None

                dataset_details = await response.json()
                return dataset_details.get("name", ""), dataset_details

        except Exception as e:
            print(f"   ⚠️  Error fetching dataset details: {e}")
            return None, None

    async def download_dataset_data(
        self, table_name: str
    ) -> tuple[list[str], list[list[Any]]] | tuple[None, None]:
        """Download dataset data from production."""
        table_url = f"{self.prod_url}/v1/api/tables/{table_name}"

        try:
            session = SingletonAiohttp.get_aiohttp_client()
            async with session.get(table_url, headers=self.headers) as response:
                if response.status != 200:
                    return await self._download_via_sql(table_name)

                result = await response.json()
                data_list = result.get("data", [])

                if not data_list or not isinstance(data_list[0], dict):
                    return None, None

                columns = list(data_list[0].keys())
                rows = [[row.get(col) for col in columns] for row in data_list]

                return columns, rows

        except Exception as e:
            print(f"   ✗ Error downloading data: {e}")
            return None, None

    async def _download_via_sql(
        self, table_name: str
    ) -> tuple[list[str], list[list[Any]]] | tuple[None, None]:
        """Fallback method using SQL API."""
        sql_url = f"{self.prod_url}/v1/api/sql"
        quoted_name = f'"{table_name}"' if "-" in table_name or " " in table_name else table_name
        body = {"query": f"SELECT * FROM {quoted_name}"}

        try:
            session = SingletonAiohttp.get_aiohttp_client()
            async with session.post(sql_url, json=body, headers=self.headers) as response:
                if response.status != 200:
                    return None, None

                result = await response.json()
                data_list = result.get("data", [])

                if not data_list:
                    return None, None

                columns = list(data_list[0].keys())
                rows = [[row.get(col) for col in columns] for row in data_list]

                return columns, rows

        except Exception:
            return None, None

    def create_csv_buffer(self, columns: list[str], rows: list[list[Any]]) -> io.BytesIO:
        """Create an in-memory CSV file from columns and rows."""
        buffer = io.BytesIO()
        text_buffer = io.StringIO()

        writer = csv.writer(text_buffer)
        writer.writerow(columns)
        writer.writerows(rows)

        csv_content = text_buffer.getvalue()
        buffer.write(csv_content.encode("utf-8"))
        buffer.seek(0)

        return buffer

    def upload_and_ingest(
        self,
        csv_buffer: io.BytesIO,
        filename: str,
        project_id: str,
        alias: str,
        description: str | None = None,
    ) -> str | None:
        """Upload CSV to S3 and ingest into local Gopie instance."""
        safe_filename = filename.replace(" ", "_").replace("/", "_") + ".csv"

        s3_path = upload_file_to_s3(
            file_content=csv_buffer.getvalue(),
            file_name=safe_filename,
            project_id=project_id,
            s3_client=self.s3_client,
            prefix="dataset",
        )

        if not s3_path:
            print("   ✗ S3 upload failed")
            return None

        try:
            dataset_id = ingest_dataset_to_gopie(
                gopie_url=self.local_url,
                project_id=project_id,
                s3_path=s3_path,
                alias=alias,
                description=description or f"Replicated from production: {alias}",
            )
            return dataset_id

        except Exception as e:
            print(f"   ✗ Ingestion failed: {e}")
            return None

    async def replicate_dataset(
        self,
        prod_project_id: str,
        local_project_id: str,
        dataset_info: dict[str, Any],
    ) -> bool:
        """Replicate a single dataset from prod to local."""
        dataset_id = dataset_info["dataset_id"]
        alias = dataset_info["alias"]
        description = dataset_info["description"]

        if dataset_id in self.cloned_datasets:
            print(f"   ⏭️  Already replicated: {alias}")
            return True

        print(f"   📦 Replicating: {alias}")

        table_name, _ = await self.get_dataset_table_name(prod_project_id, dataset_id)
        if not table_name:
            print("   ✗ Could not fetch table name")
            return False

        columns, rows = await self.download_dataset_data(table_name)
        if not columns or not rows:
            print("   ✗ Could not download data")
            return False

        print(f"   📊 Downloaded: {len(rows)} rows, {len(columns)} columns")

        csv_buffer = self.create_csv_buffer(columns, rows)

        local_dataset_id = self.upload_and_ingest(
            csv_buffer, alias, local_project_id, alias, description
        )

        if not local_dataset_id:
            return False

        self.dataset_mapping[dataset_id] = local_dataset_id
        self.cloned_datasets.add(dataset_id)

        print("   ✅ Replicated successfully")
        return True

    async def replicate_project(self, prod_project_id: str) -> str | None:
        """Replicate an entire project with all datasets from prod to local."""
        if prod_project_id in self.project_mapping:
            print("   ⏭️  Project already replicated")
            return self.project_mapping[prod_project_id]

        print(f"\n{'='*70}")
        print(f"🔄 Replicating Project: {prod_project_id}")
        print(f"{'='*70}\n")

        project_details = await self.get_project_details(prod_project_id, from_prod=True)
        if not project_details:
            print("   ✗ Could not fetch production project details")
            return None

        project_name = project_details.get("name", "Unnamed Project")
        project_description = project_details.get("description", "")

        print(f"   📂 Project Name: {project_name}")

        try:
            local_project_id = create_gopie_project(
                gopie_url=self.local_url,
                name=project_name,
                description=project_description or f"Replicated from production: {project_name}",
            )
        except SystemExit:
            print("   ✗ Could not create local project")
            return None

        self.project_mapping[prod_project_id] = local_project_id

        datasets = await self.fetch_datasets(prod_project_id)
        if not datasets:
            print("   ⚠️  No datasets found")
            return local_project_id

        print(f"   📊 Found {len(datasets)} datasets to replicate\n")

        successful = 0
        failed = 0

        for i, dataset_info in enumerate(datasets, 1):
            print(f"   [{i}/{len(datasets)}]", end=" ")

            success = await self.replicate_dataset(prod_project_id, local_project_id, dataset_info)

            if success:
                successful += 1
            else:
                failed += 1

            await asyncio.sleep(0.5)

        print(f"\n{'='*70}")
        print("📊 Replication Summary")
        print(f"{'='*70}")
        print(f"Project: {project_name}")
        print(f"Production ID: {prod_project_id}")
        print(f"Local ID: {local_project_id}")
        print(f"Datasets: {successful}/{len(datasets)} successful, {failed} failed")
        print(f"{'='*70}\n")

        return local_project_id

    async def replicate_from_json(self, json_file: str) -> dict[str, Any]:
        """
        Replicate all projects referenced in a JSON file.

        The JSON file should contain a list of dictionaries, where each dictionary
        must have a 'project_id' field. All other fields are optional and will be ignored.

        Example formats supported:
        - [{"project_id": "uuid-1", ...}, {"project_id": "uuid-2", ...}]
        - [{"Project ID": "uuid-1", ...}, {"Project ID": "uuid-2", ...}]
        """
        print(f"\n{'='*70}")
        print(f"📂 Loading from: {json_file}")
        print(f"{'='*70}\n")

        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"✗ Error loading JSON: {e}")
            return {"error": str(e)}

        if not isinstance(data, list):
            print("✗ JSON must contain a list of dictionaries")
            return {"error": "Invalid JSON structure: expected list"}

        print(f"✓ Loaded {len(data)} entries\n")

        project_ids = set()
        for item in data:
            if not isinstance(item, dict):
                continue

            project_id = item.get("project_id") or item.get("Project ID")
            if project_id:
                project_ids.add(project_id)

        project_ids = list(project_ids)

        if not project_ids:
            print("✗ No project_id fields found in JSON")
            return {"error": "No project IDs found"}

        print(f"📊 Found {len(project_ids)} unique projects to replicate\n")

        stats = {
            "total_projects": len(project_ids),
            "successful_projects": 0,
            "failed_projects": 0,
            "total_datasets": 0,
            "successful_datasets": 0,
            "project_mappings": {},
            "dataset_mappings": {},
        }

        for i, project_id in enumerate(project_ids, 1):
            print(f"[{i}/{len(project_ids)}] Processing: {project_id}")

            local_id = await self.replicate_project(project_id)

            if local_id:
                stats["successful_projects"] += 1
                stats["project_mappings"][project_id] = local_id
            else:
                stats["failed_projects"] += 1

            await asyncio.sleep(1)

        stats["total_datasets"] = len(self.dataset_mapping)
        stats["successful_datasets"] = len(self.cloned_datasets)
        stats["dataset_mappings"] = self.dataset_mapping

        return stats

    async def upload_csv_folder(
        self,
        csv_folder: str,
        project_name: str | None = None,
        project_description: str | None = None,
    ) -> dict[str, Any]:
        """
        Upload all CSV files from a local folder to a new project in local Gopie instance.

        This method leverages utilities from dataset_manager.py:
        - create_s3_bucket_if_not_exists() - Ensures S3 bucket exists (called in __init__)
        - upload_and_ingest_datasets() - Handles file upload and ingestion

        Args:
            csv_folder: Path to folder containing CSV files
            project_name: Optional project name (default: "CSV Upload Project")
            project_description: Optional project description

        Returns:
            Dictionary with upload statistics
        """
        folder_path = Path(csv_folder)

        if not folder_path.exists():
            print(f"✗ Folder does not exist: {csv_folder}")
            return {"error": "Folder not found"}

        if not folder_path.is_dir():
            print(f"✗ Path is not a directory: {csv_folder}")
            return {"error": "Not a directory"}

        csv_files = [f for f in folder_path.iterdir() if f.is_file() and f.suffix.lower() == ".csv"]

        if not csv_files:
            print(f"✗ No CSV files found in: {csv_folder}")
            return {"error": "No CSV files found"}

        print(f"\n{'='*70}")
        print(f"📂 Uploading CSV Files from: {csv_folder}")
        print(f"{'='*70}\n")
        print(f"✓ Found {len(csv_files)} CSV file(s)\n")

        project_name = project_name or "CSV Upload Project"
        project_description = (
            project_description or f"Project created from CSV files in {csv_folder}"
        )

        try:
            local_project_id = create_gopie_project(
                gopie_url=self.local_url,
                name=project_name,
                description=project_description,
            )
        except SystemExit:
            print("✗ Failed to create project")
            return {"error": "Project creation failed"}

        dataset_mappings = upload_and_ingest_datasets(
            gopie_url=self.local_url,
            project_id=local_project_id,
            s3_client=self.s3_client,
            local_files=csv_files,
        )

        successful_uploads = len(dataset_mappings)
        failed_uploads = len(csv_files) - successful_uploads

        print(f"\n{'='*70}")
        print("📊 Upload Summary")
        print(f"{'='*70}")
        print(f"Project: {project_name}")
        print(f"Project ID: {local_project_id}")
        print(f"Files: {successful_uploads}/{len(csv_files)} successful, {failed_uploads} failed")
        print(f"{'='*70}\n")

        stats = {
            "project_id": local_project_id,
            "project_name": project_name,
            "total_files": len(csv_files),
            "successful_uploads": successful_uploads,
            "failed_uploads": failed_uploads,
            "dataset_mappings": dataset_mappings,
        }

        return stats

    def print_summary(self, stats: dict[str, Any]) -> None:
        """Print final replication summary."""
        print(f"\n{'='*70}")
        print("🎉 REPLICATION COMPLETE")
        print(f"{'='*70}\n")

        if "error" in stats:
            print(f"✗ Error: {stats['error']}")
            return

        print("Projects:")
        print(f"  Total:      {stats['total_projects']}")
        print(f"  ✓ Success:  {stats['successful_projects']}")
        print(f"  ✗ Failed:   {stats['failed_projects']}")

        print("\nDatasets:")
        print(f"  Total:      {stats['total_datasets']}")
        print(f"  ✓ Success:  {stats['successful_datasets']}")

        if stats["successful_projects"] > 0:
            success_rate = (stats["successful_projects"] / stats["total_projects"]) * 100
            print(f"\nSuccess Rate: {success_rate:.1f}%")

        print(f"\n📁 Production: {self.prod_url}")
        print(f"📁 Local:      {self.local_url}")

        print(f"\n{'='*70}\n")


async def main():
    parser = argparse.ArgumentParser(
        description="Replicate projects from production or upload CSV files to local Gopie instance",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Replicate all projects from a JSON file
  python -m tests.scripts.replicate_prod_to_local \\
    --prod-url http://localhost:8000 \\
    --local-url http://localhost:8001 \\
    --json-file tests/chat_server_tests/output/golden_dataset.json

  # Replicate a specific project
  python -m tests.scripts.replicate_prod_to_local \\
    --prod-url http://localhost:8000 \\
    --local-url http://localhost:8001 \\
    --project-id b7711501-e8ee-4804-82dd-5fe5af817dcd

  # Upload CSV files from a local folder
  python -m tests.scripts.replicate_prod_to_local \\
    --local-url http://localhost:8001 \\
    --csv-folder /path/to/csv/files \\
    --project-name "My Test Project"
        """,
    )

    parser.add_argument("--prod-url", help="Production Gopie API URL (required for replication)")
    parser.add_argument("--local-url", required=True, help="Local Gopie API URL")
    parser.add_argument(
        "--json-file",
        help="JSON file containing project references (list of dicts with project_id)",
    )
    parser.add_argument(
        "--project-id", help="Specific project ID to replicate (alternative to --json-file)"
    )
    parser.add_argument(
        "--csv-folder",
        help="Path to folder containing CSV files to upload (alternative to replication)",
    )
    parser.add_argument(
        "--project-name",
        help="Project name for CSV upload (optional, default: 'CSV Upload Project')",
    )
    parser.add_argument(
        "--project-description", help="Project description for CSV upload (optional)"
    )

    args = parser.parse_args()

    csv_mode = args.csv_folder is not None
    replication_mode = args.json_file or args.project_id

    if csv_mode and replication_mode:
        print("Error: Cannot use --csv-folder with --json-file or --project-id")
        print("Choose either CSV upload mode OR replication mode")
        sys.exit(1)

    if not csv_mode and not replication_mode:
        print("Error: Must provide either:")
        print("  - --csv-folder (to upload CSV files)")
        print("  - --json-file or --project-id (to replicate from production)")
        sys.exit(1)

    if replication_mode and not args.prod_url:
        print("Error: --prod-url is required for replication mode")
        sys.exit(1)

    replicator = ProdToLocalReplicator(
        prod_url=args.prod_url or "",
        local_url=args.local_url,
    )

    try:
        if csv_mode:
            stats = await replicator.upload_csv_folder(
                csv_folder=args.csv_folder,
                project_name=args.project_name,
                project_description=args.project_description,
            )

            if "error" not in stats:
                if stats.get("failed_uploads", 0) == 0:
                    print("✓ All CSV files uploaded successfully!")
                    sys.exit(0)
                else:
                    print("⚠ Some CSV files failed to upload")
                    sys.exit(1)
            else:
                print(f"✗ Upload failed: {stats['error']}")
                sys.exit(1)

        elif args.json_file:
            stats = await replicator.replicate_from_json(args.json_file)
            replicator.print_summary(stats)

            if "error" not in stats and stats.get("failed_projects", 0) == 0:
                print("✓ All projects replicated successfully!")
                sys.exit(0)
            else:
                print("⚠ Some projects or datasets failed to replicate")
                sys.exit(1)

        else:
            local_id = await replicator.replicate_project(args.project_id)
            stats = {
                "total_projects": 1,
                "successful_projects": 1 if local_id else 0,
                "failed_projects": 0 if local_id else 1,
                "total_datasets": len(replicator.dataset_mapping),
                "successful_datasets": len(replicator.cloned_datasets),
            }

            replicator.print_summary(stats)

            if "error" not in stats and stats.get("failed_projects", 0) == 0:
                print("✓ Project replicated successfully!")
                sys.exit(0)
            else:
                print("⚠ Project replication failed")
                sys.exit(1)

    except KeyboardInterrupt:
        print("\n\n⚠ Replication interrupted by user")
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
