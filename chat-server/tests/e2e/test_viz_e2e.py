import pytest

from tests.e2e.utils.dataset_manager import (
    cleanup_project,
    setup_project_and_upload_datasets,
)
from tests.e2e.viz_utils.per_example_workflow import PerExampleWorkflow
from tests.test_config import TestConfig

CHAT_SERVER_URL = TestConfig.CHAT_SERVER_URL
GOPIE_API_URL = TestConfig.GOPIE_API_URL
VIZ_OUTPUT_DIR = TestConfig.VIZ_OUTPUT_DIR


@pytest.mark.asyncio
async def test_visualization_e2e(request, capfd):
    """
    End-to-end test for visualization generation using per-example workflow.

    This test:
    1. Extracts vega dataset names from examples
    2. Creates a project and uploads vega datasets to Gopie
    3. Processes each example through complete workflow (image → test case → run)
    4. Reports final results
    5. Cleans up the project
    """
    limit = request.config.getoption("--limit", default=None)
    if limit is not None:
        limit = int(limit)

    project_id = None

    try:
        with capfd.disabled():
            print("\n=== Extracting vega dataset names from examples ===")

        vega_dataset_names = PerExampleWorkflow.get_vega_dataset_names()

        if not vega_dataset_names:
            pytest.skip("No vega datasets found in examples")

        with capfd.disabled():
            print(f"Found {len(vega_dataset_names)} unique vega dataset(s)")
            print(
                f"\n=== Creating project and uploading {len(vega_dataset_names)} vega datasets ==="
            )

            project_id = setup_project_and_upload_datasets(
                gopie_url=GOPIE_API_URL,
                vega_dataset_names=vega_dataset_names,
            )

        workflow = PerExampleWorkflow(
            gopie_api_endpoint=GOPIE_API_URL,
            project_id=project_id,
            output_dir=VIZ_OUTPUT_DIR,
        )

        with capfd.disabled():
            results = await workflow.process_all_examples()

        success_results = [r for r in results if r.status == "success"]
        if limit is not None:
            success_results = success_results[:limit]

        passed = len(
            [
                r
                for r in success_results
                if r.test_result
                and r.test_result.get("success")
                and r.test_result.get("evaluation", {}).get("score", 0) >= 8
            ]
        )
        failed = len(success_results) - passed

        with capfd.disabled():
            print("\n=== Final Test Results ===")
            print(f"Passed: {passed}/{len(success_results)}")
            print(f"Failed: {failed}/{len(success_results)}")

        if failed > 0:
            pytest.fail(f"{failed} visualization test(s) failed")

    finally:
        if project_id:
            with capfd.disabled():
                print(f"\n=== Cleaning up project {project_id} ===")
                cleanup_project(gopie_url=GOPIE_API_URL, project_id=project_id)
