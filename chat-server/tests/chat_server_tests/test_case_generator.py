import argparse
import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from app.core.session import SingletonAiohttp
from app.utils.model_registry.model_provider import get_configured_llm_for_node
from tests.e2e.utils.dataset_manager import GOPIE_ORG_ID, GOPIE_USER_ID
from tests.test_config import TestConfig


class TestCases(BaseModel):
    query: str = Field(
        description="generated query for the dataset",
        min_length=1,
    )
    project_id: str = Field(
        description="Project identifier for the dataset",
        default="",
    )
    expected_dataset_id: list[str] = Field(description="", default=[])
    dataset_id: str = Field(description="", default="")
    query_type: Literal["data", "viz"] = Field(description="")
    data_type: Literal["single", "multi"] = Field(description="")


class TestCasesList(BaseModel):
    test_cases: list[TestCases] = Field(description="List of test cases", default_factory=list)


class TestCaseGenerator:
    def __init__(self, project_ids: list[str], gopie_api_endpoint: str):
        self.gopie_api_endpoint = gopie_api_endpoint
        self.project_ids = project_ids
        self.headers = {
            "accept": "application/json",
            "X-Organization-ID": GOPIE_ORG_ID,
            "X-User-ID": GOPIE_USER_ID,
        }

    async def fetch_datasets_for_project(self, project_id: str) -> list[str]:
        print(f"Fetching datasets for project: {project_id}")
        url = f"{self.gopie_api_endpoint}/v1/api/projects/{project_id}/datasets"
        params = {"limit": 10, "page": 1}
        dataset_ids = []

        try:
            session = SingletonAiohttp.get_aiohttp_client()
            async with session.get(url, params=params, headers=self.headers) as response:
                response.raise_for_status()
                response_json = await response.json()

            for data in response_json:
                dataset_ids.append(data.get("id", ""))

            print(f"Found {len(dataset_ids)} datasets")
        except Exception as e:
            print(f"Error fetching datasets for project {project_id}: {e}")

        return dataset_ids

    async def fetch_schema_for_dataset(self, dataset_id: str, project_id: str):
        details_url = (
            f"{self.gopie_api_endpoint}/v1/api/projects/{project_id}/datasets/{dataset_id}"
        )

        try:
            session = SingletonAiohttp.get_aiohttp_client()
            async with session.get(details_url, headers=self.headers) as response:
                response.raise_for_status()
                dataset_details = await response.json()
        except Exception as e:
            print(f"Error fetching dataset details for {dataset_id}: {e}")
            return None

        dataset_name = dataset_details.get("name", "")
        print(f"Processing dataset: {dataset_name}")
        summary_url = f"{self.gopie_api_endpoint}/v1/api/summary/{dataset_name}"

        try:
            session = SingletonAiohttp.get_aiohttp_client()
            async with session.get(summary_url, headers=self.headers) as response:
                response.raise_for_status()
                dataset_summary = await response.json()
        except Exception as e:
            print(f"Error fetching dataset summary for {dataset_name}: {e}")
            dataset_summary = {"summary": ""}

        sql_url = f"{self.gopie_api_endpoint}/v1/api/sql"
        body = {
            "query": f"SELECT * FROM {dataset_name} LIMIT 5",
        }

        try:
            session = SingletonAiohttp.get_aiohttp_client()
            async with session.post(sql_url, json=body, headers=self.headers) as response:
                response.raise_for_status()
                sample_data = await response.json()
        except Exception as e:
            print(f"Error fetching sample data for {dataset_name}: {e}")
            sample_data = {}

        dataset_schema = {
            "project_id": project_id,
            "dataset_id": dataset_id,
            "name": dataset_details.get("alias", ""),
            "dataset_name": dataset_details.get("name", ""),
            "dataset_description": dataset_details.get("description", ""),
            "summary": dataset_summary.get("summary", ""),
            "project_custom_prompt": dataset_details.get("project_custom_prompt", ""),
            "dataset_custom_prompt": dataset_details.get("dataset_custom_prompt", ""),
            "sample_data": sample_data,
        }

        return dataset_schema

    async def generate_test_cases_with_llm(
        self,
        datasets_schema: list[dict],
        test_type: str = "both",
    ) -> TestCasesList:
        print(f"Generating test cases for {len(datasets_schema)} datasets (type: {test_type})")
        all_test_cases: TestCasesList = TestCasesList(test_cases=[])

        if test_type in ["single", "both"]:
            print("Generating single dataset test cases...")
            for i, dataset_schema in enumerate(datasets_schema, 1):
                dataset_name = dataset_schema.get("dataset_name", "unknown")
                print(f"  {i}/{len(datasets_schema)}: {dataset_name}")

                prompt = self._create_single_dataset_prompt(
                    dataset_schema,
                )

                single_test_cases = await self._call_llm(prompt)
                print(f"    → Generated {len(single_test_cases.test_cases)} test cases")
                all_test_cases.test_cases.extend(single_test_cases.test_cases)

        if test_type in ["multi", "both"] and len(datasets_schema) > 1:
            print("Generating multi-dataset test cases...")
            multi_prompt = self._create_multi_dataset_prompt(datasets_schema)

            multi_cases = await self._call_llm(multi_prompt)
            print(f"  → Generated {len(multi_cases.test_cases)} multi-dataset test cases")
            all_test_cases.test_cases.extend(multi_cases.test_cases)

        print(f"Total test cases generated: {len(all_test_cases.test_cases)}")
        return all_test_cases

    def _format_dataset_schema(self, dataset_schema: dict) -> str:
        formatted = f"""
Dataset: {dataset_schema.get('name', 'Unknown')}
Project id: {dataset_schema.get('project_id', 'Unknown')}
Dataset id: {dataset_schema.get('dataset_id', "Unknown")}
Table Name: {dataset_schema.get('dataset_name', 'Unknown')}
Description: {dataset_schema.get('dataset_description', 'No description available')}
Summary: {dataset_schema.get('summary', 'No summary available')}
"""

        sample_data = dataset_schema.get("sample_data", {})
        if sample_data and isinstance(sample_data, dict):
            if sample_data.get("columns"):
                formatted += f"Columns: {', '.join(sample_data.get('columns', []))}\n"

            if sample_data.get("data") and len(sample_data.get("data", [])) > 0:
                formatted += "Sample Rows:\n"
                for i, row in enumerate(sample_data.get("data", [])):
                    formatted += f"  Row {i+1}: {row}\n"

        if dataset_schema.get("dataset_custom_prompt"):
            formatted += f"Custom Instructions: {dataset_schema.get('dataset_custom_prompt')}\n"

        return formatted.strip()

    def _format_multiple_datasets_schema(self, datasets_schema: list[dict]) -> str:
        """Format multiple dataset schemas into a readable string for LLM prompts."""
        formatted_datasets = []

        for i, schema in enumerate(datasets_schema, 1):
            dataset_str = f"Dataset {i}:\n" + self._format_dataset_schema(schema)
            formatted_datasets.append(dataset_str)

        return "\n\n".join(formatted_datasets)

    def _create_single_dataset_prompt(self, dataset_schema: dict) -> str:
        formatted_schema = self._format_dataset_schema(dataset_schema)

        prompt = f"""
You are a test case generator for a data analytics application. Generate natural language questions that users would ask about the dataset.

Given the following dataset schema, generate 10 diverse user questions for this dataset:

{formatted_schema}

Generate realistic questions that users would ask about the data in the dataset, ranging from simple to advanced:

NOTE: Keep expected_datasets field empty for single dataset cases

Requirements:
1. Generate exactly 10 test cases for this dataset
2. Mix of question types:
   - 5-6 data questions (asking for specific information, filtering, aggregations, comparisons)
   - 4-5 visualization questions (requesting charts, graphs, plots, trends)
3. Make questions realistic and natural - how a real user would ask
4. Vary complexity from simple ("How many...") to advanced analytical questions
5. Use natural language, not SQL - these are user questions, not technical queries
6. Base questions on the actual columns and data available in the dataset

Examples of good questions:
- "How many records are there in total?"
- "What is the average value of [column]?"
- "Show me a chart of [metric] by [category]"
- "Which [category] has the highest [value]?"
- "Can you create a trend analysis of [metric] over time?"
"""

        return prompt

    def _create_multi_dataset_prompt(self, datasets_schema: list[dict]) -> str:
        formatted_schemas = self._format_multiple_datasets_schema(datasets_schema)

        prompt = f"""
You are a test case generator for a data analytics application. Generate natural language questions that users would ask when they want to analyze multiple datasets together.

Given the following dataset schemas, generate 15 user questions that require analysis across MULTIPLE datasets:

{formatted_schemas}

Generate realistic cross-dataset analysis questions that users would ask:

NOTE: Keep the dataset_id in the response empty for multidataset cases

Requirements:
1. Generate exactly 15 multi-dataset test cases
2. Mix of question types:
   - 10-11 data questions (comparing, joining, correlating data across datasets)
   - 4-5 visualization questions (comparison charts, combined visualizations)
3. Each question must require information from 2 or more datasets
4. Make questions realistic and natural - how a real user would ask
5. Vary complexity from simple comparisons to advanced analytical questions
6. Use natural language, not SQL - these are user questions, not technical queries
7. Identify meaningful relationships between the datasets

Examples of good multi-dataset questions:
- "Compare the trends between [dataset1 metric] and [dataset2 metric]"
- "How does [metric from dataset1] correlate with [metric from dataset2]?"
- "Show me a combined visualization of [data from multiple datasets]"
- "Which dataset shows higher values for [common metric]?"
- "Create a dashboard combining key insights from all available datasets"
"""

        return prompt

    async def _call_llm(self, prompt: str) -> TestCasesList:
        try:
            llm = get_configured_llm_for_node(
                node_name="identify_datasets", config=RunnableConfig(), schema=TestCasesList
            )

            result = await llm.ainvoke(prompt)
            return result
        except Exception as e:
            print(f"Error calling LLM: {e}")
            raise e

    async def generate_for_all_projects(self, test_type: str = "both") -> None:
        base_dir = Path(__file__).parent
        target_output_dir = base_dir / "output"
        print(f"Starting test case generation (output: {target_output_dir}, type: {test_type})")

        os.makedirs(target_output_dir, exist_ok=True)

        project_ids = self.project_ids

        if not project_ids:
            print("No project ids provided!")
            return

        print(f"Processing {len(project_ids)} projects")
        all_test_cases: TestCasesList = TestCasesList(test_cases=[])

        for i, project_id in enumerate(project_ids, 1):
            if not project_id:
                print(f"Skipping empty project ID at index {i}")
                continue

            print(f"\nProject {i}/{len(project_ids)}: {project_id}")

            dataset_ids = await self.fetch_datasets_for_project(project_id)

            if not dataset_ids:
                print(f"No datasets found for project {project_id}")
                continue

            print(f"Fetching schemas for {len(dataset_ids)} datasets...")
            datasets_with_schemas = []
            for j, dataset_id in enumerate(dataset_ids, 1):
                schema = await self.fetch_schema_for_dataset(
                    dataset_id=dataset_id, project_id=project_id
                )
                if schema is not None:
                    datasets_with_schemas.append(schema)
                else:
                    print(f"Failed to fetch schema for dataset: {dataset_id}")

            if not datasets_with_schemas:
                print(f"No valid schemas found for project {project_id}")
                continue

            print(f"Successfully fetched {len(datasets_with_schemas)} schemas")

            project_test_cases = await self.generate_test_cases_with_llm(
                datasets_with_schemas, test_type
            )

            print(f"Generated {len(project_test_cases.test_cases)} test cases for this project")
            all_test_cases.test_cases.extend(project_test_cases.test_cases)

        if all_test_cases and all_test_cases.test_cases:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            json_filename = os.path.join(str(target_output_dir), f"golden_dataset_{timestamp}.json")

            # Serialize full test cases to JSON
            serializable_cases = []
            for tc in all_test_cases.test_cases:
                item: dict[str, Any] = {
                    "project_id": tc.project_id,
                    "dataset_id": tc.dataset_id,
                    "query": tc.query,
                    "query_type": tc.query_type,
                    "data_type": tc.data_type,
                }
                # Include expected_dataset_id if present
                if getattr(tc, "expected_dataset_id", None):
                    item["expected_dataset_id"] = tc.expected_dataset_id
                serializable_cases.append(item)

            with open(json_filename, "w", encoding="utf-8") as f:
                json.dump(serializable_cases, f, ensure_ascii=False, indent=2)

            single_count = sum(
                1 for case in all_test_cases.test_cases if case.data_type == "single"
            )
            multi_count = sum(1 for case in all_test_cases.test_cases if case.data_type == "multi")
            data_count = sum(1 for case in all_test_cases.test_cases if case.query_type == "data")
            viz_count = sum(1 for case in all_test_cases.test_cases if case.query_type == "viz")

            print("\n=== Test Case Generation Complete ===")
            print(f"Total projects: {len(project_ids)}")
            print(f"Total test cases: {len(all_test_cases.test_cases)}")
            print(f"  - Single dataset: {single_count}")
            print(f"  - Multi dataset: {multi_count}")
            print(f"  - Data queries: {data_count}")
            print(f"  - Visualization queries: {viz_count}")
            print(f"Output file: {json_filename}")
        else:
            print("No test cases generated. JSON file will not be created.")


async def main():
    parser = argparse.ArgumentParser(description="Generate test cases for chat server evaluation")
    parser.add_argument(
        "--project-ids",
        required=True,
        help="Comma-separated list of project IDs to generate test cases for",
    )
    parser.add_argument(
        "--type",
        choices=["single", "multi", "both"],
        default="both",
        help="Type of test cases to generate: single, multi, or both (default: both)",
    )

    args = parser.parse_args()

    print("=== Starting Test Case Generator ===")

    project_ids = [pid.strip() for pid in args.project_ids.split(",") if pid.strip()]

    if not project_ids:
        print("ERROR: No valid project IDs provided.")
        print(
            "Usage: python -m tests.evaluator.chat_server_tests.test_case_generator --project-ids=id1,id2"
        )
        return

    gopie_url = TestConfig.GOPIE_API_URL

    print(f"Using project IDs: {', '.join(project_ids)}")
    print(f"API Endpoint: {gopie_url}")
    print(f"Test Type: {args.type}")

    generator = TestCaseGenerator(
        project_ids=project_ids,
        gopie_api_endpoint=gopie_url,
    )

    try:
        await generator.generate_for_all_projects(
            test_type=args.type,
        )
    finally:
        await SingletonAiohttp.close_aiohttp_client()

    print("=== Finished ===")


if __name__ == "__main__":
    asyncio.run(main())
