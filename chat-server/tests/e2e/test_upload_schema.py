import asyncio
import traceback

import requests
from dotenv import load_dotenv

load_dotenv()

server_url = "http://localhost:8001/api/v1/upload_schema"

# Real project and dataset IDs
PROJECT_ID = "b26ad6ba-9c23-4c32-ac34-3fc8a6aa86a1"
DATASET_ID = "db0ee4dc-d75f-4d3d-8672-119a7cf77968"

datasets = [
    {"project_id": PROJECT_ID, "dataset_id": DATASET_ID, "result": True},
    {
        "project_id": "invalid-project-id-format",
        "dataset_id": DATASET_ID,
        "result": False,
    },
]


async def process_single_schema_upload(schema_data):
    schema_copy = schema_data.copy()
    test_url = server_url
    expected_result = schema_copy.pop("result")

    print(f"Processing schema upload for dataset: {schema_copy['dataset_id']}")
    results = {
        "dataset_id": schema_copy["dataset_id"],
        "passed": False,
        "message": "",
        "details": {},
        "expected_result": expected_result,
    }

    try:
        response = requests.post(
            test_url,
            json=schema_copy,
            headers={"Content-Type": "application/json"},
        )

        try:
            response_data = response.json()
        except Exception as e:
            print(f"Error parsing JSON: {e}")
            response_data = {"text": response.text}

        print(f"Response: {response_data}")

        api_success = response.status_code == 200 and response_data.get("success") is True

        if (expected_result and api_success) or (not expected_result and not api_success):
            results["passed"] = True
            if expected_result:
                results["message"] = "Schema upload successful as expected"
            else:
                results["message"] = "Schema upload failed as expected"
            print("✅ Test passed")
        else:
            print("❌ Test failed")
            if expected_result:
                results[
                    "message"
                ] = f"Expected success but got failure with status code {response.status_code}"
            else:
                results[
                    "message"
                ] = f"Expected failure but got success with status code {response.status_code}"
            print(f"Status code: {response.status_code}")

        results["details"] = response_data
        return results

    except Exception as e:
        print(f"API request failed: {str(e)}")
        print(traceback.format_exc())
        results["message"] = f"Error: {str(e)}"
        return results


async def run_schema_tests():
    print(f"\nRunning schema upload tests against {server_url}")

    results = []

    for dataset in datasets:
        print(f"Running schema upload test for dataset_id: {dataset['dataset_id']}")
        result = await process_single_schema_upload(dataset)
        results.append(result)

    passed = sum(1 for r in results if r["passed"] is True)
    failed = sum(1 for r in results if r["passed"] is False)

    print("\n== Results Summary ==")
    print(f"Total tests: {len(results)}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")

    if failed > 0:
        print("\n== Failed Tests ==")
        for ft in results:
            if not ft["passed"]:
                print(f"Dataset ID: {ft['dataset_id']}")
                print(f"Message: {ft['message']}\n")

    return results


if __name__ == "__main__":
    asyncio.run(run_schema_tests())
