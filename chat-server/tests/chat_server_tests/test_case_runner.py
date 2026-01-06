import argparse
import asyncio
import json
import os
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.core.session import SingletonAiohttp
from tests.e2e.utils.test_utils import (
    create_evaluation_chain,
    send_chat_request,
)
from tests.performance_tools.performance_tracker import PerformanceTracker
from tests.test_config import TestConfig


class TestCaseRunner:
    def __init__(self, use_dspy: bool = False):
        """
        Initialize test case runner.

        Args:
            use_dspy: If True, use DSPy optimized evaluator instead of manual chain
        """
        self.use_dspy = use_dspy

        if use_dspy:
            # Import and initialize DSPy evaluator
            from tests.dspy.evaluator import OptimizedEvaluator

            try:
                self.evaluator = OptimizedEvaluator()
                print(f"✓ Using DSPy optimized evaluator: {self.evaluator.evaluator_path}")
            except FileNotFoundError as e:
                print(f"✗ Error: {e}")
                print("\nPlease run DSPy optimization first:")
                print("  python -m tests.dspy.optimize_evaluator")
                sys.exit(1)
        else:
            # Use traditional manual evaluation chain
            self.evaluation_chain = create_evaluation_chain()

    def get_model_configuration(self) -> dict[str, str]:
        """Capture current model configuration from settings."""
        from app.core.config import settings

        return {
            "fast_model": settings.FAST_MODEL or settings.DEFAULT_LLM_MODEL,
            "balanced_model": settings.BALANCED_MODEL or settings.DEFAULT_LLM_MODEL,
            "advanced_model": settings.ADVANCED_MODEL or settings.DEFAULT_LLM_MODEL,
            "default_model": settings.DEFAULT_LLM_MODEL,
            "evaluator_type": "dspy" if self.use_dspy else "manual",
        }

    async def run_test_case(self, test_case: dict[str, Any]) -> dict[str, Any]:
        try:
            formatted_test_case = self._format_test_case(test_case)

            # Track request time only (not evaluation time)
            request_start = time.time()
            response = await send_chat_request(formatted_test_case, TestConfig.CHAT_SERVER_URL)
            request_time = time.time() - request_start

            if "error" in response:
                return {
                    "success": False,
                    "error": response["error"],
                    "request_time": request_time,
                    "chat_server_response": response,
                    "evaluation": {
                        "evaluation_score": 0,
                        "reasoning": f"API Error: {response['error']}",
                        "summary": "API request failed",
                    },
                }

            comprehensive_response = self._build_comprehensive_response(response)
            expected_result = self._create_expected_result(test_case)

            # Use appropriate evaluator based on flag
            if self.use_dspy:
                # DSPy evaluator - no manual prompt formatting needed
                evaluation = self.evaluator.evaluate(
                    generated_answer=comprehensive_response,
                    expected_result=expected_result,
                )
            else:
                # Manual evaluation chain with hardcoded prompt
                formatted_generated_answer = self._format_generated_answer(comprehensive_response)
                formatted_expected_result = self._format_expected_result(expected_result, test_case)

                evaluation = await self.evaluation_chain.ainvoke(
                    {
                        "generated_answer": formatted_generated_answer,
                        "expected_result": formatted_expected_result,
                    }
                )

            return {
                "success": True,
                "request_time": request_time,
                "chat_server_response": response,
                "comprehensive_response": comprehensive_response,
                "evaluation": evaluation,
                "expected_result": expected_result,
            }

        except Exception as e:
            error_msg = f"Error running test case: {str(e)}"
            return {
                "success": False,
                "request_time": 0.0,
                "error": error_msg,
                "evaluation": {
                    "evaluation_score": 0,
                    "reasoning": f"Execution Error: {str(e)}",
                    "summary": "Test execution failed",
                },
            }

    def _format_test_case(self, test_case: dict[str, Any]) -> dict[str, Any]:
        formatted = {
            "messages": [{"role": "user", "content": test_case["query"]}],
            "model": "test",
            "user": "test",
            "stream": True,
        }

        metadata = {}
        if test_case["data_type"] == "single" and test_case["dataset_id"]:
            metadata["dataset_id"] = test_case["dataset_id"]

        if test_case.get("project_id"):
            metadata["project_id"] = test_case["project_id"]

        if metadata:
            formatted["metadata"] = metadata

        return formatted

    def _build_comprehensive_response(self, response: dict[str, Any]) -> dict[str, Any]:
        return {
            "ai_response": response["final_response"],
            "datasets_used": response["selected_datasets"],
            "sql_queries_generated": response["generated_sql_queries"],
            "processing_steps": response["tool_messages"],
            "visualization_results": response.get("visualization_results", []),
            "metadata": {
                "dataset_count": len(response["selected_datasets"]),
                "sql_query_count": len(response["generated_sql_queries"]),
                "processing_step_count": len(response["tool_messages"]),
                "visualization_count": len(response.get("visualization_results", [])),
            },
        }

    def _create_expected_result(self, test_case: dict[str, Any]) -> dict[str, Any]:
        query_type = test_case.get("query_type", "")
        data_type = test_case.get("data_type", "")

        expected = {
            "query_type": query_type,
            "data_type": data_type,
            "expected_datasets": [],
            "description": "",
        }

        if query_type == "data" and data_type == "single":
            expected["description"] = (
                "Should provide accurate data analysis from a single dataset. "
                "Note: Dataset identification in 'datasets_used' is NOT required for single-dataset queries."
            )
        elif query_type == "data" and data_type == "multi":
            expected["description"] = "Should analyze and correlate data across multiple datasets"
        elif query_type == "viz" and data_type == "single":
            expected["description"] = (
                "Should generate appropriate visualization from a single dataset. "
                "Note: Dataset identification in 'datasets_used' is NOT required for single-dataset queries."
            )
        elif query_type == "viz" and data_type == "multi":
            expected[
                "description"
            ] = "Should create comparative or combined visualizations across datasets"
        else:
            expected["description"] = "Should process the query appropriately"

        if data_type == "multi" and test_case.get("expected_dataset_id"):
            expected_datasets = test_case["expected_dataset_id"]
            if isinstance(expected_datasets, str):
                expected_datasets = [expected_datasets]
            expected["expected_datasets"] = expected_datasets
            expected["description"] += f" using datasets: {', '.join(expected_datasets)}"

        return expected

    def _format_generated_answer(self, comprehensive_response: dict[str, Any]) -> str:
        """Format the comprehensive response into a readable string for evaluation."""
        parts = []

        # AI Response
        if comprehensive_response.get("ai_response"):
            parts.append(f"AI Response: {comprehensive_response['ai_response']}")

        # Datasets Used
        if comprehensive_response.get("datasets_used"):
            datasets = comprehensive_response["datasets_used"]
            parts.append(f"Datasets Used: {', '.join(datasets)} (Count: {len(datasets)})")

        # SQL Queries
        if comprehensive_response.get("sql_queries_generated"):
            sql_queries = comprehensive_response["sql_queries_generated"]
            parts.append(f"SQL Queries Generated: {len(sql_queries)} queries")
            for i, query in enumerate(sql_queries, 1):
                parts.append(f"  SQL Query {i}: {query}")

        # Processing Steps
        if comprehensive_response.get("processing_steps"):
            steps = comprehensive_response["processing_steps"]
            parts.append(f"Processing Steps: {len(steps)} steps completed")

        # Visualizations
        if comprehensive_response.get("visualization_results"):
            viz_results = comprehensive_response["visualization_results"]
            parts.append(f"Visualizations: {len(viz_results)} visualizations created")

        # Metadata Summary
        metadata = comprehensive_response.get("metadata", {})
        parts.append(
            f"Summary: {metadata.get('dataset_count', 0)} datasets, "
            f"{metadata.get('sql_query_count', 0)} SQL queries, "
            f"{metadata.get('processing_step_count', 0)} processing steps, "
            f"{metadata.get('visualization_count', 0)} visualizations"
        )

        return "\n".join(parts)

    def _format_expected_result(
        self, expected_result: dict[str, Any], test_case: dict[str, Any]
    ) -> str:
        """Format the expected result into a readable string for evaluation."""
        parts = []

        # Query context
        parts.append(f"Original Query: {test_case.get('query', '')}")
        parts.append(f"Query Type: {expected_result.get('query_type', 'unknown')}")
        parts.append(f"Data Type: {expected_result.get('data_type', 'unknown')}")

        # Expected behavior
        parts.append(f"Expected Behavior: {expected_result.get('description', '')}")

        # Expected datasets (only for multi-dataset queries)
        if expected_result.get("expected_datasets"):
            datasets = expected_result["expected_datasets"]
            parts.append(f"Expected Datasets: {', '.join(datasets)}")

        # Project context
        if test_case.get("project_id"):
            parts.append(f"Project ID: {test_case['project_id']}")

        return "\n".join(parts)

    async def run_test_cases(
        self,
        test_cases: list[dict[str, Any]],
        input_file: str = "",
    ) -> list[dict[str, Any]]:
        """
        Run test cases with automatic performance tracking.

        Args:
            test_cases: List of test cases to run
            input_file: Original input file path for naming output

        Returns:
            List of updated test cases with results
        """
        total = len(test_cases)
        print(f"Running {total} test cases...")

        # Get model configuration
        model_config = self.get_model_configuration()

        # Display configuration
        print(f"\nModel Configuration:")
        print(f"  FAST:     {model_config['fast_model']}")
        print(f"  BALANCED: {model_config['balanced_model']}")
        print(f"  ADVANCED: {model_config['advanced_model']}")
        print(f"  EVALUATOR: {model_config['evaluator_type'].upper()}\n")

        updated_test_cases = []
        request_times = []

        for i, test_case in enumerate(test_cases, 1):
            print(f"[{i}/{total}] Processing: {test_case['query'][:50]}...")

            result = await self.run_test_case(test_case)
            request_times.append(result.get("request_time", 0.0))

            updated_test_case = test_case.copy()

            if result["success"]:
                # Save complete chat server response
                updated_test_case["chat_server_response"] = result["chat_server_response"]
                # Save AI evaluation (numeric score format)
                score = result["evaluation"].get("evaluation_score", 0)
                updated_test_case["ai_evaluation"] = {
                    "score": float(score),
                    "reasoning": result["evaluation"].get("reasoning", ""),
                    "summary": result["evaluation"].get("summary", ""),
                }
                updated_test_case["request_time"] = result["request_time"]
            else:
                updated_test_case["chat_server_response"] = result.get("chat_server_response", {})
                updated_test_case["error"] = result["error"]
                updated_test_case["request_time"] = result.get("request_time", 0.0)
                updated_test_case["ai_evaluation"] = {
                    "score": 0.0,
                    "reasoning": result["evaluation"].get("reasoning", ""),
                    "summary": result["evaluation"].get(
                        "summary", "Error occurred during execution"
                    ),
                }

            updated_test_cases.append(updated_test_case)

            status = self._get_status_icon(result)
            print(f"[{i}/{total}] {status} Completed (took {result.get('request_time', 0):.2f}s)")

            if i < total:
                await asyncio.sleep(0.5)

        # Calculate statistics
        stats = self._calculate_stats(updated_test_cases)
        timing_stats = self._calculate_timing_stats(request_times)

        # Save to performance history (always enabled)
        tracker = PerformanceTracker()

        # Create output directory
        output_dir = Path(__file__).parent / "output"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate results filename based on input file
        if input_file:
            base_name = Path(input_file).stem  # e.g., "golden_dataset_20250806_010759"
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            results_file = str(output_dir / f"{base_name}_results_run_{timestamp}.json")
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            results_file = str(output_dir / f"test_results_run_{timestamp}.json")

        run_id = tracker.save_run(
            model_config=model_config,
            summary={
                "timing": timing_stats,
                "total": stats["total"],
                "scores": stats["scores"],
                "score_stats": stats["score_stats"],
                "errors": stats["errors"],
            },
            notes="",  # Can be extended later if needed
            test_cases=updated_test_cases,
            results_file=results_file,
        )

        print(f"\n✓ Performance tracked: run_id = {run_id}")
        print(f"✓ Performance history: {tracker.history_file}")

        return updated_test_cases, stats, timing_stats, model_config

    def _create_response_summary(self, result: dict[str, Any]) -> str:
        if not result["success"]:
            return f"ERROR: {result['error']}"

        response = result["chat_server_response"]
        evaluation = result["evaluation"]

        # Handle both numeric score and legacy formats
        if "evaluation_score" in evaluation:
            parts = [f"EVALUATION SCORE: {evaluation['evaluation_score']}/10"]
        else:
            parts = [f"EVALUATION: {evaluation.get('correct', 'unknown')}"]

        if evaluation.get("reasoning"):
            parts.append(f"REASONING: {evaluation['reasoning']}")

        if response.get("final_response"):
            final_resp = response["final_response"][:200]
            if len(response["final_response"]) > 200:
                final_resp += "..."
            parts.append(f"RESPONSE: {final_resp}")

        if response.get("selected_datasets"):
            parts.append(f"DATASETS: {', '.join(response['selected_datasets'])}")

        if response.get("generated_sql_queries"):
            parts.append(f"SQL_COUNT: {len(response['generated_sql_queries'])}")

        if response.get("visualization_results"):
            parts.append(f"VIZ_COUNT: {len(response['visualization_results'])}")

        return " | ".join(parts)

    def _get_status_icon(self, result: dict[str, Any]) -> str:
        if not result["success"]:
            return "✗"

        # Use numeric score format (0-10)
        score = result["evaluation"].get("evaluation_score", 0)
        if score >= 8:
            return "✓"  # Good score (8-10)
        elif score >= 5:
            return "◐"  # Partial score (5-7)
        else:
            return "✗"  # Poor score (0-4)

    def _is_passed(self, test_case: dict[str, Any]) -> bool:
        """Check if a test case passed (score >= 8)."""
        if "error" in test_case:
            return False
        eval_data = test_case.get("ai_evaluation", {})
        return eval_data.get("score", 0) >= 8

    def _calculate_timing_stats(self, request_times: list[float]) -> dict[str, float]:
        """Calculate timing statistics from request times."""
        if not request_times:
            return {
                "avg_request_time": 0.0,
                "median_request_time": 0.0,
                "min_request_time": 0.0,
                "max_request_time": 0.0,
                "total_time": 0.0,
            }

        return {
            "avg_request_time": statistics.mean(request_times),
            "median_request_time": statistics.median(request_times),
            "min_request_time": min(request_times),
            "max_request_time": max(request_times),
            "total_time": sum(request_times),
        }

    def save_results(self, test_cases: list[dict[str, Any]], output_file: str) -> None:
        if not test_cases:
            print("WARNING: No results to save")
            return

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(test_cases, f, ensure_ascii=False, indent=2)

        print(f"Results saved to: {output_file}")

    def print_summary(
        self,
        test_cases: list[dict[str, Any]],
        stats: dict[str, Any] = None,
        timing_stats: dict[str, float] = None,
        model_config: dict[str, str] = None,
    ) -> None:
        """Print summary with optional timing and model configuration."""
        if not test_cases:
            print("No test results available")
            return

        if stats is None:
            stats = self._calculate_stats(test_cases)

        self._display_summary(stats, timing_stats, model_config)

    def _calculate_stats(self, test_cases: list[dict[str, Any]]) -> dict[str, Any]:
        total = len(test_cases)
        scores = []
        errors = 0

        for tc in test_cases:
            if "error" in tc:
                errors += 1
            elif "ai_evaluation" in tc:
                score = tc["ai_evaluation"].get("score", 0)
                scores.append(score)

        # Calculate basic statistics
        score_stats = {}
        if scores:
            sorted_scores = sorted(scores)
            score_stats = {
                "average": sum(scores) / len(scores),
                "min": min(scores),
                "max": max(scores),
                "median": sorted_scores[len(scores) // 2],
            }

        return {
            "total": total,
            "scores": scores,
            "score_stats": score_stats,
            "errors": errors,
        }

    def _display_summary(
        self,
        stats: dict[str, Any],
        timing_stats: dict[str, float] = None,
        model_config: dict[str, str] = None,
    ) -> None:
        """Display comprehensive summary with timing and model config."""
        total = stats["total"]
        score_stats = stats.get("score_stats", {})
        errors = stats["errors"]

        print("\n" + "=" * 70)
        print("TEST EXECUTION SUMMARY")
        print("=" * 70)

        # Model configuration
        if model_config:
            print("\nModel Configuration:")
            print(f"  FAST_MODEL:     {model_config['fast_model']}")
            print(f"  BALANCED_MODEL: {model_config['balanced_model']}")
            print(f"  ADVANCED_MODEL: {model_config['advanced_model']}")
            print(f"  EVALUATOR:      {model_config['evaluator_type'].upper()}")

        # Timing metrics
        if timing_stats:
            print("\nPerformance Metrics:")
            print(f"  Total Time:       {timing_stats['total_time']:.2f}s")
            print(f"  Average per Test: {timing_stats['avg_request_time']:.2f}s")
            print(f"  Median per Test:  {timing_stats['median_request_time']:.2f}s")
            print(f"  Min Time:         {timing_stats['min_request_time']:.2f}s")
            print(f"  Max Time:         {timing_stats['max_request_time']:.2f}s")

        # Score statistics
        print(f"\nTest Results:")
        print(f"  Total Test Cases: {total}")
        if score_stats:
            print(f"  Average Score:    {score_stats['average']:.2f}/10")
            print(f"  Median Score:     {score_stats['median']:.2f}/10")
            print(f"  Min Score:        {score_stats['min']:.2f}/10")
            print(f"  Max Score:        {score_stats['max']:.2f}/10")
        if errors > 0:
            print(f"  Errors:           {errors}")

        print("=" * 70)


def find_latest_json_dataset(directory: str = str(Path(__file__).parent)) -> Optional[str]:
    pattern = "golden_dataset_*.json"
    files = [
        f
        for f in Path(directory).glob(pattern)
        if "_results" not in f.stem and "_labeled" not in f.stem
    ]

    if not files:
        return None

    def extract_timestamp(file_path: Path) -> str:
        filename = file_path.stem
        parts = filename.split("_")
        if len(parts) >= 3:
            return f"{parts[-2]}_{parts[-1]}"
        return "00000000_000000"

    latest_file = max(files, key=extract_timestamp)
    return str(latest_file)


def load_test_cases(input_file: str) -> list[dict[str, Any]]:
    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)
        if isinstance(data, list):
            return data
        # If somehow stored as an object with a key
        return data.get("test_cases", [])


def filter_test_cases(
    test_cases: list[dict[str, Any]],
    data_type: Optional[str] = None,
    query_type: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Filter test cases by data type and/or query type."""
    filtered = test_cases

    if data_type:
        filtered = [tc for tc in filtered if tc.get("data_type") == data_type]

    if query_type:
        filtered = [tc for tc in filtered if tc.get("query_type") == query_type]

    return filtered


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run and evaluate chat server test cases with automatic performance tracking",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with manual evaluator (default)
  python -m tests.chat_server_tests.test_case_runner

  # Run with DSPy evaluator
  python -m tests.chat_server_tests.test_case_runner --use-dspy

  # Run specific test type with DSPy
  python -m tests.chat_server_tests.test_case_runner --use-dspy --data-type single

  # Run only data queries
  python -m tests.chat_server_tests.test_case_runner --query-type data

Note:
  - Timing and performance tracking are ALWAYS enabled
  - Results saved to: golden_dataset_*_results_run_TIMESTAMP.json
  - Performance history saved to: performance_history.json
        """,
    )

    parser.add_argument(
        "--data-type",
        type=str,
        choices=["single", "multi"],
        help="Filter test cases by data type (single or multi dataset)",
    )

    parser.add_argument(
        "--query-type",
        type=str,
        choices=["data", "viz"],
        help="Filter test cases by query type (data or visualization)",
    )

    parser.add_argument(
        "--use-dspy",
        action="store_true",
        help="Use DSPy optimized evaluator (replaces manual evaluation chain)",
    )

    return parser.parse_args()


async def main() -> None:
    args = parse_arguments()

    input_file = find_latest_json_dataset()

    if not input_file:
        print("No JSON dataset file found. Please generate one first using test_case_generator.py")
        sys.exit(1)

    if not os.path.exists(input_file):
        print(f"Error: File '{input_file}' not found")
        sys.exit(1)

    test_cases = load_test_cases(input_file)
    if not test_cases:
        print("No test cases found in the input file")
        sys.exit(1)

    print(f"Using dataset: {input_file}")
    print(f"Loaded {len(test_cases)} test cases")

    filtered_test_cases = filter_test_cases(test_cases, args.data_type, args.query_type)

    if not filtered_test_cases:
        print(
            f"No test cases match the filter criteria (data_type={args.data_type}, query_type={args.query_type})"
        )
        sys.exit(1)

    if len(filtered_test_cases) < len(test_cases):
        filter_info = []
        if args.data_type:
            filter_info.append(f"data_type={args.data_type}")
        if args.query_type:
            filter_info.append(f"query_type={args.query_type}")
        print(f"Filtered to {len(filtered_test_cases)} test cases ({', '.join(filter_info)})")

    try:
        runner = TestCaseRunner(use_dspy=args.use_dspy)
        updated_test_cases, stats, timing_stats, model_config = await runner.run_test_cases(
            filtered_test_cases, input_file=input_file
        )

        # Generate output filename with timestamp
        output_dir = Path(__file__).parent / "output"
        output_dir.mkdir(parents=True, exist_ok=True)
        base_name = Path(input_file).stem
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = str(output_dir / f"{base_name}_results_run_{timestamp}.json")

        runner.save_results(updated_test_cases, output_file)
        runner.print_summary(updated_test_cases, stats, timing_stats, model_config)

    finally:
        await SingletonAiohttp.close_aiohttp_client()


if __name__ == "__main__":
    asyncio.run(main())
