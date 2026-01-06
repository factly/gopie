import argparse
import asyncio
import json
import sys
from typing import List, Optional

from app.core.config import settings
from app.core.session import SingletonAiohttp
from tests.e2e.utils.dataset_manager import GOPIE_ORG_ID, GOPIE_USER_ID


class SchemaUploader:
    def __init__(self, base_url: str = "http://localhost:8000"):
        """
        Initialize the Schema Uploader.

        Args:
            base_url: Base URL for the chat server API
        """
        self.base_url = base_url.rstrip("/")
        self.api_base = f"{self.base_url}/api/v1"
        self.gopie_api_endpoint = settings.GOPIE_API_ENDPOINT or "http://localhost:8001"
        self.headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "X-Organization-id": GOPIE_ORG_ID,
            "X-User-ID": GOPIE_USER_ID,
        }

    async def fetch_datasets_for_project(self, project_id: str) -> List[str]:
        """
        Fetch all dataset IDs for a given project.

        Args:
            project_id: The project ID to fetch datasets for

        Returns:
            List of dataset IDs
        """
        print(f"Fetching datasets for project: {project_id}")

        # Try to get from local projects_datasets.json file first
        try:
            with open("projects_datasets.json", "r") as f:
                projects_data = json.load(f)

            for project in projects_data:
                if project.get("project_id") == project_id:
                    dataset_ids = [dataset["dataset_id"] for dataset in project.get("datasets", [])]
                    print(
                        f"Found {len(dataset_ids)} datasets in local file for project {project_id}"
                    )
                    return dataset_ids

        except FileNotFoundError:
            print("Local projects_datasets.json not found, fetching from API...")
        except Exception as e:
            print(f"Error reading local file: {e}, fetching from API...")

        # Fallback to API if local file not available or project not found
        url = f"{self.gopie_api_endpoint}/v1/api/projects/{project_id}/datasets"
        params = {"limit": 100, "page": 1}
        dataset_ids = []

        try:
            session = SingletonAiohttp.get_aiohttp_client()
            async with session.get(url, params=params, headers=self.headers) as response:
                response.raise_for_status()
                response_json = await response.json()

            for data in response_json["results"]:
                dataset_id = data.get("id", "")
                if dataset_id:
                    dataset_ids.append(dataset_id)

            print(f"Found {len(dataset_ids)} datasets from API for project {project_id}")
        except Exception as e:
            print(f"Error fetching datasets for project {project_id}: {e}")
            return []

        return dataset_ids

    async def upload_schema(self, project_id: str, dataset_id: str) -> bool:
        """
        Upload schema for a single dataset.

        Args:
            project_id: The project ID
            dataset_id: The dataset ID

        Returns:
            True if successful, False otherwise
        """
        url = f"{self.api_base}/upload_schema"
        payload = {"project_id": project_id, "dataset_id": dataset_id}

        try:
            session = SingletonAiohttp.get_aiohttp_client()
            async with session.post(url, json=payload, headers=self.headers) as response:
                response_json = await response.json()

                if response.status == 200:
                    print(f"✓ Successfully uploaded schema for dataset {dataset_id}")
                    if response_json.get("message"):
                        print(f"  Message: {response_json['message']}")
                    return True
                else:
                    print(f"✗ Failed to upload schema for dataset {dataset_id}")
                    print(f"  Status: {response.status}")
                    print(f"  Response: {response_json}")
                    return False

        except Exception as e:
            print(f"✗ Error uploading schema for dataset {dataset_id}: {e}")
            return False

    async def upload_schemas_for_project(
        self, project_id: str, dataset_id: Optional[str] = None
    ) -> dict:
        """
        Upload schemas for all datasets in a project or a single dataset.

        Args:
            project_id: The project ID
            dataset_id: Optional specific dataset ID to upload

        Returns:
            Dictionary with upload results
        """
        print(f"=== Starting schema upload for project {project_id} ===")

        if dataset_id:
            # Upload single dataset
            print(f"Uploading single dataset: {dataset_id}")
            success = await self.upload_schema(project_id, dataset_id)
            return {
                "project_id": project_id,
                "total_datasets": 1,
                "successful_uploads": 1 if success else 0,
                "failed_uploads": 0 if success else 1,
                "success_rate": 100.0 if success else 0.0,
            }

        # Upload all datasets for project
        dataset_ids = await self.fetch_datasets_for_project(project_id)

        if not dataset_ids:
            print("No datasets found for this project")
            return {
                "project_id": project_id,
                "total_datasets": 0,
                "successful_uploads": 0,
                "failed_uploads": 0,
                "success_rate": 0.0,
            }

        print(f"Starting upload for {len(dataset_ids)} datasets...")

        successful_uploads = 0
        failed_uploads = 0

        for i, dataset_id in enumerate(dataset_ids, 1):
            print(f"\nUploading dataset {i}/{len(dataset_ids)}: {dataset_id}")

            success = await self.upload_schema(project_id, dataset_id)
            if success:
                successful_uploads += 1
            else:
                failed_uploads += 1

            # Small delay between uploads to avoid overwhelming the server
            await asyncio.sleep(0.5)

        success_rate = (successful_uploads / len(dataset_ids)) * 100 if dataset_ids else 0

        print(f"\n=== Upload Complete for Project {project_id} ===")
        print(f"Total datasets: {len(dataset_ids)}")
        print(f"Successful uploads: {successful_uploads}")
        print(f"Failed uploads: {failed_uploads}")
        print(f"Success rate: {success_rate:.1f}%")

        return {
            "project_id": project_id,
            "total_datasets": len(dataset_ids),
            "successful_uploads": successful_uploads,
            "failed_uploads": failed_uploads,
            "success_rate": success_rate,
        }

    async def upload_schemas_for_multiple_projects(self, project_ids: List[str]) -> List[dict]:
        """
        Upload schemas for multiple projects.

        Args:
            project_ids: List of project IDs

        Returns:
            List of upload results for each project
        """
        print(f"=== Starting schema upload for {len(project_ids)} projects ===")

        results = []

        for i, project_id in enumerate(project_ids, 1):
            print(f"\n--- Processing project {i}/{len(project_ids)}: {project_id} ---")

            result = await self.upload_schemas_for_project(project_id)
            results.append(result)

            # Delay between projects
            if i < len(project_ids):
                print("Waiting before next project...")
                await asyncio.sleep(2)

        # Summary
        total_datasets = sum(result["total_datasets"] for result in results)
        total_successful = sum(result["successful_uploads"] for result in results)
        total_failed = sum(result["failed_uploads"] for result in results)
        overall_success_rate = (total_successful / total_datasets) * 100 if total_datasets else 0

        print("\n=== Overall Summary ===")
        print(f"Projects processed: {len(project_ids)}")
        print(f"Total datasets: {total_datasets}")
        print(f"Total successful uploads: {total_successful}")
        print(f"Total failed uploads: {total_failed}")
        print(f"Overall success rate: {overall_success_rate:.1f}%")

        return results

    async def test_connection(self) -> bool:
        """
        Test connection to the upload schema endpoint.

        Returns:
            True if connection is successful, False otherwise
        """
        print("Testing connection to upload schema endpoint...")

        # Test with a dummy request to see if endpoint is reachable
        url = f"{self.api_base}/upload_schema"
        test_payload = {"project_id": "test", "dataset_id": "test"}

        try:
            session = SingletonAiohttp.get_aiohttp_client()
            async with session.post(url, json=test_payload, headers=self.headers) as response:
                # We expect this to fail with validation or processing error, but endpoint should be reachable
                if response.status in [200, 400, 422, 500]:  # Endpoint is reachable
                    print(f"✓ Connection successful (status: {response.status})")
                    return True
                else:
                    print(f"✗ Unexpected status code: {response.status}")
                    return False

        except Exception as e:
            print(f"✗ Connection failed: {e}")
            return False


async def main():
    parser = argparse.ArgumentParser(description="Upload dataset schemas to the chat server")
    parser.add_argument("--project-id", required=True, help="Project ID to upload schemas for")
    parser.add_argument("--dataset-id", help="Specific dataset ID to upload (optional)")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Base URL for the API")
    parser.add_argument("--test-connection", action="store_true", help="Test connection only")

    args = parser.parse_args()

    uploader = SchemaUploader(base_url=args.base_url)

    try:
        if args.test_connection:
            success = await uploader.test_connection()
            sys.exit(0 if success else 1)

        result = await uploader.upload_schemas_for_project(args.project_id, args.dataset_id)

        # Exit with appropriate code
        if result["failed_uploads"] == 0:
            print("\n✓ All uploads completed successfully!")
            sys.exit(0)
        else:
            print(f"\n⚠ {result['failed_uploads']} uploads failed")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\nUpload interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)
    finally:
        await SingletonAiohttp.close_aiohttp_client()


if __name__ == "__main__":
    asyncio.run(main())
