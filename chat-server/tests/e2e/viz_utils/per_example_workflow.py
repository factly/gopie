"""
Per-example visualization test workflow.

This module implements a systematic approach where each Vega-Lite example
goes through the complete workflow before moving to the next example:

1. Extract Python code from example
2. Execute code → Generate chart image
3. Extract dataset names from code
4. Upload dataset to Gopie (if not already cached)
5. Fetch schema from Gopie
6. Generate test case with LLM
7. Run test case immediately
8. Log result (pass/fail/skip)

This approach provides better incremental validation and easier debugging
compared to batch processing.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Optional

import aiohttp
from altair import Chart
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from app.utils.model_registry.model_provider import get_configured_llm_for_node
from tests.e2e.utils.dataset_manager import GOPIE_ORG_ID, GOPIE_USER_ID
from tests.e2e.viz_utils.io_utils import VizIOManager
from tests.e2e.viz_utils.viz_test_case_runner import run_viz_test_case
from tests.e2e.viz_utils.viz_utils import populate_examples
from tests.test_config import TestConfig


class VizTestCase(BaseModel):
    query: str = Field(description="generated visualization query for the dataset(s)", min_length=1)
    project_id: str = Field(description="Project identifier for the dataset(s)", default="")
    dataset_id: str = Field(
        description="Single-dataset id; empty for multi-dataset queries", default=""
    )
    sql_queries: list[str] = Field(
        description="SQL queries that retrieve the full dataset(s) used for visualization",
        default_factory=list,
    )
    image_path: str = Field(
        description="Path to reference image",
        default="",
    )


class ExampleResult(BaseModel):
    example_name: str
    status: str  # 'success', 'skip', 'error'
    image_path: Optional[str] = None
    datasets: list[str] = Field(default_factory=list)
    test_case: Optional[VizTestCase] = None
    test_result: Optional[dict[str, Any]] = None
    error_message: Optional[str] = None


class PerExampleWorkflow:
    @staticmethod
    def get_vega_dataset_names() -> list[str]:
        """
        Extract all unique vega dataset names from examples.
        This is used for uploading datasets to Gopie before running workflow.

        Returns:
            List of unique dataset names
        """
        import re

        DATASET_REGEX = re.compile(r"\bdata\.(\w+)")
        examples = populate_examples()
        all_dataset_names = []

        for example in examples:
            code = example.get("code", "") if isinstance(example, dict) else ""
            if isinstance(code, str) and code.strip():
                names = DATASET_REGEX.findall(code)
                all_dataset_names.extend(names)

        unique_names = list(dict.fromkeys(all_dataset_names))
        return unique_names

    def _build_result_dict(self, result: ExampleResult) -> dict[str, Any]:
        """Build result dictionary from ExampleResult."""
        result_dict = {
            "example_name": result.example_name,
            "status": result.status,
            "image_path": result.image_path,
            "datasets": result.datasets,
        }

        if result.test_case:
            tc = result.test_case
            result_dict.update(
                {
                    "project_id": tc.project_id,
                    "dataset_id": tc.dataset_id,
                    "query": tc.query,
                    "sql_queries": tc.sql_queries,
                }
            )

        if result.test_result:
            result_dict["test_result"] = {
                "success": result.test_result.get("success", False),
                "evaluation": result.test_result.get("evaluation", {}),
                "error": result.test_result.get("error"),
            }

        if result.error_message:
            result_dict["error_message"] = result.error_message

        return result_dict

    def _save_result_to_json(self, result: ExampleResult):
        """Save a single result to the JSON file incrementally."""
        json_path = self.io.build_viz_json_path(timestamp=self._json_timestamp)

        # Load existing results or start fresh
        existing_results = self.io.load_json(json_path) if json_path.exists() else []

        # Append new result
        existing_results.append(self._build_result_dict(result))

        # Save updated results
        self.io.save_json(json_path, existing_results)

    def __init__(
        self,
        gopie_api_endpoint: str,
        project_id: str,
        output_dir: str,
    ):
        """
        Initialize the per-example workflow.

        Args:
            gopie_api_endpoint: Gopie API base URL
            project_id: Pre-created project ID with datasets uploaded
            output_dir: Output directory for artifacts
        """
        self.gopie_api_endpoint = gopie_api_endpoint
        self.project_id = project_id
        self.output_dir = output_dir
        self.io = VizIOManager(output_dir)
        self.io.ensure_all_dirs()

        self.headers = {
            "accept": "application/json",
            "X-Organization-ID": GOPIE_ORG_ID,
            "X-User-ID": GOPIE_USER_ID,
        }

        self.dataset_cache: dict[str, str] = {}

        self.stats = {
            "total": 0,
            "success": 0,
            "skipped": 0,
            "errors": 0,
        }

        self.results: list[ExampleResult] = []

        # Single timestamp for all results in this run
        from datetime import datetime

        self._json_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    def _normalize_name(self, name: str) -> str:
        return (name or "").strip().lower().replace("-", "_").replace(" ", "_")

    async def _fetch_schema_for_dataset(
        self, dataset_id: str, project_id: str
    ) -> dict[str, Any] | None:
        details_url = (
            f"{self.gopie_api_endpoint}/v1/api/projects/{project_id}/datasets/{dataset_id}"
        )

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(details_url, headers=self.headers, ssl=False) as response:
                    response.raise_for_status()
                    dataset_details = await response.json()
        except Exception as e:
            print(f"    ❌ Error fetching dataset details: {e}")
            return None

        dataset_name = dataset_details.get("name", "")

        async def fetch_summary() -> dict[str, Any]:
            summary_url = f"{self.gopie_api_endpoint}/v1/api/summary/{dataset_name}"
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        summary_url, headers=self.headers, ssl=False
                    ) as response:
                        response.raise_for_status()
                        return await response.json()
            except Exception:
                return {"summary": ""}

        async def fetch_sample_data() -> dict[str, Any]:
            sql_url = f"{self.gopie_api_endpoint}/v1/api/sql"
            body = {"query": f"SELECT * FROM {dataset_name} LIMIT 5"}
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        sql_url, json=body, headers=self.headers, ssl=False
                    ) as response:
                        response.raise_for_status()
                        return await response.json()
            except Exception:
                return {}

        dataset_summary, sample_data = await asyncio.gather(fetch_summary(), fetch_sample_data())

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

    def _format_dataset_schema(self, dataset_schema: dict[str, Any]) -> str:
        """Format dataset schema for LLM prompt."""
        formatted = f"""
Dataset: {dataset_schema.get('name', 'Unknown')}
Project id: {dataset_schema.get('project_id', 'Unknown')}
Dataset id: {dataset_schema.get('dataset_id', 'Unknown')}
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

    def _format_multiple_datasets_schema(self, datasets_schema: list[dict[str, Any]]) -> str:
        """Format multiple dataset schemas for LLM prompt."""
        parts: list[str] = []
        for i, schema in enumerate(datasets_schema, 1):
            parts.append(f"Dataset {i}:\n" + self._format_dataset_schema(schema))
        return "\n\n".join(parts)

    def _encode_image_as_data_url(self, image_path: str) -> str:
        """Encode image as data URL for LLM."""
        return self.io.data_url_for_image_path(image_path)

    def _create_prompt_for_image(
        self, image_path: str, datasets_schema: list[dict[str, Any]]
    ) -> list:
        """Create LLM prompt for test case generation."""
        formatted = self._format_multiple_datasets_schema(datasets_schema)
        data_url = self._encode_image_as_data_url(image_path)

        system = SystemMessage(
            content=(
                """
You are a visualization test case generator for a data analytics application.
Given the reference chart image and the schema of the dataset(s),
write ONE natural language question that a user would ask to produce
a chart that matches the reference image as closely as possible.

Requirements:
1. Output exactly one concise natural language visualization question.
2. Specify chart type and encodings when useful (axes, grouping, color).
3. Use only columns present in the provided schema(s).
4. Do not include SQL.
                """
            )
        )

        human = HumanMessage(
            content=[
                {"type": "text", "text": f"Relevant dataset schema(s):\n{formatted}"},
                {"type": "image_url", "image_url": {"url": data_url, "detail": "auto"}},
            ]
        )

        return [system, human]

    async def _call_llm(self, prompt: Any) -> VizTestCase:
        """Call LLM to generate test case."""
        try:
            llm = get_configured_llm_for_node(
                node_name="identify_datasets", config=RunnableConfig(), schema=VizTestCase
            )
            result = await llm.ainvoke(prompt)
            return result
        except Exception as e:
            print(f"    ❌ Error calling LLM: {e}")
            raise e

    def _extract_dataset_names(self, code: str) -> list[str]:
        """Extract dataset names from example code."""
        import re

        DATASET_REGEX = re.compile(r"\bdata\.(\w+)")
        names = DATASET_REGEX.findall(code)
        return list(dict.fromkeys(names))

    def _save_chart_image(self, chart: Chart) -> str:
        """Save chart as image."""
        path = self.io.save_chart_image(chart, subdir="images", prefix="chart")
        return path

    def _execute_python_code(self, code: str) -> tuple[Optional[str], Optional[str]]:
        """
        Execute Python code and generate chart image.

        Returns:
            Tuple of (image_path, error_message)
        """
        try:
            exec_globals = {
                "__builtins__": __builtins__,
            }

            exec("import pandas as pd", exec_globals)
            exec("import numpy as np", exec_globals)
            exec("import altair as alt", exec_globals)
            exec("from vega_datasets import data", exec_globals)

            exec(code, exec_globals)

            chart = exec_globals.get("chart", None)
            if not chart:
                return None, "No Altair chart object found in executed code"

            image_path = self._save_chart_image(chart=chart)
            return image_path, None

        except Exception as e:
            return None, str(e)

    async def _find_dataset_in_gopie(self, dataset_name: str) -> Optional[str]:
        """
        Find dataset ID in Gopie by name.
        Returns dataset_id if found, None otherwise.
        """
        normalized_name = self._normalize_name(dataset_name)

        if normalized_name in self.dataset_cache:
            return self.dataset_cache[normalized_name]

        url = f"{self.gopie_api_endpoint}/v1/api/projects/{self.project_id}/datasets"
        params = {"limit": 100, "page": 1}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, params=params, headers=self.headers, ssl=False
                ) as response:
                    response.raise_for_status()
                    response_json = await response.json()
                    datasets = list(response_json.get("results", []))

            for ds in datasets:
                key_alias = self._normalize_name(ds.get("alias", ""))
                key_name = self._normalize_name(ds.get("name", ""))

                if normalized_name in {key_alias, key_name}:
                    dataset_id = ds.get("id", "")
                    if dataset_id:
                        self.dataset_cache[normalized_name] = dataset_id
                        return dataset_id

            return None

        except Exception as e:
            print(f"    ❌ Error finding dataset in Gopie: {e}")
            return None

    async def process_example(
        self, example_name: str, example_code: str, example_index: int, total_examples: int
    ) -> ExampleResult:
        """
        Complete workflow for ONE example.

        Args:
            example_name: Name of the example
            example_code: Python code from example
            example_index: Current example number (1-indexed)
            total_examples: Total number of examples

        Returns:
            ExampleResult with status and details
        """
        print(f"\n{'='*70}")
        print(f"[{example_index}/{total_examples}] Processing: {example_name}")
        print(f"{'='*70}")

        result = ExampleResult(example_name=example_name, status="error")

        # Step 1: Execute code and generate image
        print("  → Step 1: Generating chart image...")
        image_path, error = self._execute_python_code(example_code)

        if error or not image_path:
            result.status = "skip"
            result.error_message = f"Failed to generate image: {error}"
            print(f"    ⚠️  Skipped - {result.error_message}")
            return result

        print(f"    ✓ Image saved: {Path(image_path).name}")
        result.image_path = image_path

        # Step 2: Extract dataset names
        print("  → Step 2: Extracting dataset names...")
        dataset_names = self._extract_dataset_names(example_code)

        if not dataset_names:
            result.status = "skip"
            result.error_message = "No datasets found in code"
            print(f"    ⚠️  Skipped - {result.error_message}")
            return result

        print(f"    ✓ Found datasets: {', '.join(dataset_names)}")
        result.datasets = dataset_names

        # Step 3: Find datasets in Gopie (assumes already uploaded)
        print("  → Step 3: Finding datasets in Gopie...")
        dataset_ids = []
        for ds_name in dataset_names:
            ds_id = await self._find_dataset_in_gopie(ds_name)
            if ds_id:
                dataset_ids.append(ds_id)
                print(f"    ✓ Found '{ds_name}' (ID: {ds_id[:8]}...)")
            else:
                print(f"    ⚠️  Dataset '{ds_name}' not found in Gopie")

        if not dataset_ids:
            result.status = "skip"
            result.error_message = "No matching datasets found in Gopie"
            print(f"    ⚠️  Skipped - {result.error_message}")
            return result

        # Step 4: Fetch schemas
        print(f"  → Step 4: Fetching {len(dataset_ids)} schema(s)...")
        fetch_tasks = [
            self._fetch_schema_for_dataset(dataset_id=did, project_id=self.project_id)
            for did in dataset_ids
        ]
        schemas_results = await asyncio.gather(*fetch_tasks, return_exceptions=True)
        schemas = [s for s in schemas_results if isinstance(s, dict)]

        if not schemas:
            result.status = "error"
            result.error_message = "Failed to fetch schemas"
            print(f"    ❌ {result.error_message}")
            return result

        print(f"    ✓ Fetched {len(schemas)} schema(s)")

        # Step 5: Generate test case with LLM
        print("  → Step 5: Generating test case with LLM...")
        try:
            prompt = self._create_prompt_for_image(image_path=image_path, datasets_schema=schemas)
            test_case = await self._call_llm(prompt)

            unique_project_ids = {s.get("project_id", "") for s in schemas if s.get("project_id")}
            unique_dataset_ids = [s.get("dataset_id", "") for s in schemas if s.get("dataset_id")]
            unique_dataset_ids = [d for d in unique_dataset_ids if d]

            test_case.project_id = next(iter(unique_project_ids)) if unique_project_ids else ""
            test_case.dataset_id = unique_dataset_ids[0] if len(unique_dataset_ids) == 1 else ""

            dataset_names_for_sql = [
                s.get("dataset_name", "") for s in schemas if s.get("dataset_name")
            ]
            test_case.sql_queries = [f'SELECT * FROM "{dn}"' for dn in dataset_names_for_sql]
            test_case.image_path = image_path

            result.test_case = test_case
            print(f"    ✓ Test case generated: {test_case.query[:60]}...")

        except Exception as e:
            result.status = "error"
            result.error_message = f"LLM generation failed: {e}"
            print(f"    ❌ {result.error_message}")
            return result

        # Step 6: Run test case immediately
        print("  → Step 6: Running test case...")
        try:
            case_dict = {
                "project_id": test_case.project_id,
                "dataset_id": test_case.dataset_id,
                "query": test_case.query,
                "sql_queries": test_case.sql_queries,
                "image_path": test_case.image_path,
            }

            test_result = await run_viz_test_case(case_dict)
            result.test_result = test_result

            if test_result.get("success"):
                evaluation = test_result.get("evaluation", {})
                score = evaluation.get("score", 0)
                passed = score >= 8
                status_emoji = "✅" if passed else "❌"
                result.status = "success" if passed else "error"
                print(
                    f"    {status_emoji} Test {'PASSED' if passed else 'FAILED'} (score: {score}/10)"
                )
            else:
                result.status = "error"
                result.error_message = test_result.get("error", "Unknown error")
                print(f"    ❌ Test error: {result.error_message}")

        except Exception as e:
            result.status = "error"
            result.error_message = f"Test execution failed: {e}"
            print(f"    ❌ {result.error_message}")

        return result

    async def process_all_examples(self) -> list[ExampleResult]:
        """
        Process all Vega-Lite examples one by one.

        Returns:
            List of ExampleResult objects
        """
        print("\n" + "=" * 70)
        print("Starting Per-Example Visualization Test Workflow")
        print("=" * 70)

        # Load all examples
        examples = populate_examples()
        self.stats["total"] = len(examples)

        print(f"\nLoaded {len(examples)} example(s)")
        print(f"Output directory: {self.output_dir}")
        print(f"Project ID: {self.project_id}")

        # Process each example
        for i, example in enumerate(examples, 1):
            example_name = example.get("name", f"example_{i}")
            code = example.get("code", "") if isinstance(example, dict) else ""

            if not isinstance(code, str) or not code.strip():
                print(f"\n[{i}/{len(examples)}] Skipping '{example_name}' - no code")
                self.results.append(
                    ExampleResult(
                        example_name=example_name,
                        status="skip",
                        error_message="No code found",
                    )
                )
                self.stats["skipped"] += 1
                continue

            result = await self.process_example(
                example_name=example_name,
                example_code=code,
                example_index=i,
                total_examples=len(examples),
            )

            self.results.append(result)

            # Save result immediately to JSON
            self._save_result_to_json(result)

            # Update statistics
            if result.status == "success":
                self.stats["success"] += 1
            elif result.status == "skip":
                self.stats["skipped"] += 1
            else:
                self.stats["errors"] += 1

            # Print progress summary
            self._print_progress()

        # Final summary
        self._print_final_summary()

        return self.results

    def _print_progress(self):
        """Print current progress statistics."""
        processed = self.stats["success"] + self.stats["skipped"] + self.stats["errors"]
        print(f"\n  Progress: {processed}/{self.stats['total']} | ", end="")
        print(f"✅ {self.stats['success']} | ⚠️  {self.stats['skipped']} | ❌ {self.stats['errors']}")

    def _print_final_summary(self):
        """Print final summary of all results."""
        json_path = self.io.build_viz_json_path(timestamp=self._json_timestamp)

        print("\n" + "=" * 70)
        print("FINAL SUMMARY")
        print("=" * 70)
        print(f"Total examples: {self.stats['total']}")
        print(f"Successfully processed: {self.stats['success']}")
        print(f"Skipped: {self.stats['skipped']}")
        print(f"Errors: {self.stats['errors']}")
        print(
            f"Success rate: {self.stats['success'] / self.stats['total'] * 100:.1f}%"
            if self.stats["total"] > 0
            else "N/A"
        )
        print(f"\nResults saved to: {json_path}")
        print("=" * 70)


async def main():
    """Main entry point for per-example workflow."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Process Vega-Lite examples with per-example workflow"
    )
    parser.add_argument(
        "--project-id",
        required=True,
        help="Gopie project ID with uploaded vega datasets",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help=f"Output directory (default: {TestConfig.VIZ_OUTPUT_DIR})",
    )

    args = parser.parse_args()

    endpoint = TestConfig.GOPIE_API_URL
    output_dir = args.output_dir or TestConfig.VIZ_OUTPUT_DIR
    project_id = args.project_id

    print("Configuration:")
    print(f"  Project ID: {project_id}")
    print(f"  API Endpoint: {endpoint}")
    print(f"  Output Directory: {output_dir}")

    workflow = PerExampleWorkflow(
        gopie_api_endpoint=endpoint,
        project_id=project_id,
        output_dir=output_dir,
    )

    await workflow.process_all_examples()

    # Exit with error code if any tests failed
    if workflow.stats["errors"] > 0:
        exit(1)


if __name__ == "__main__":
    asyncio.run(main())
