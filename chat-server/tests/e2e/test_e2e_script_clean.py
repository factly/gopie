"""
E2E Tests for GoPie Chat Server.

This module contains pytest-compatible end-to-end tests for the chat completion API.
Tests are organized into single dataset, multi dataset, and combined test suites.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

import pytest

from .multi_dataset_cases import MULTI_DATASET_TEST_CASES
from .single_dataset_cases import SINGLE_DATASET_TEST_CASES
from .terminal_formatter import TerminalFormatter
from .test_utils import (
    create_evaluation_chain,
    get_test_cases,
    get_user_query,
    handle_expected_error,
    initialize_test_results,
    send_chat_request,
    update_results_with_evaluation,
)

# Configuration
URL = "http://localhost:8001/api/v1/chat/completions"


async def process_test_case(
    test_case: Dict[str, Any],
    evaluation_chain,
    formatter: Optional[TerminalFormatter] = None,
    test_num: Optional[int] = None,
    total_tests: Optional[int] = None
) -> Dict[str, Any]:
    """Process a single test case."""
    user_query = get_user_query(test_case)

    if formatter and test_num and total_tests:
        formatter.print_test_case_header(test_num, total_tests, user_query)

    expected_result = test_case.get("expected_result", {})
    results = initialize_test_results(user_query, expected_result)

    try:
        if formatter:
            formatter.print_processing_status("Processing query...")

        response = await send_chat_request(test_case, URL)

        # Handle API errors
        if "error" in response:
            if expected_result.get("error_expected") or expected_result.get("execution_failure"):
                return handle_expected_error(results, formatter)
            else:
                raise Exception(response["error"])

        # Check for unexpected success when error was expected
        if expected_result.get("error_expected") or expected_result.get("execution_failure"):
            raise Exception("Expected error but API call succeeded")

        # Process successful response
        if formatter:
            formatter.print_response_summary(
                response["final_response"],
                response["selected_datasets"],
                response["generated_sql_queries"],
                response["tool_messages"]
            )
            formatter.print_evaluation_status()

        # Evaluate response
        evaluation = await evaluation_chain.ainvoke({
            "generated_answer": response["final_response"],
            "expected_result": expected_result,
        })

        update_results_with_evaluation(results, evaluation, response, expected_result, formatter)
        return results

    except Exception as e:
        if formatter:
            formatter.print_error(f"Test failed: {str(e)}")

        results.update({
            "reasoning": f"Error: {str(e)}",
            "error": str(e),
            "status": "error"
        })
        return results


async def run_test_suite(
    test_cases: List[Dict[str, Any]],
    test_type: str,
    evaluation_chain,
    use_formatter: bool = True
) -> List[Dict[str, Any]]:
    """Run a suite of test cases."""
    start_time = datetime.now()
    formatter = TerminalFormatter(use_colors=True) if use_formatter else None

    if formatter:
        formatter.print_framework_header(start_time)
        formatter.print_test_suite_info(len(test_cases), test_type, URL)

    results = []
    for i, test_case in enumerate(test_cases, 1):
        result = await process_test_case(test_case, evaluation_chain, formatter, i, len(test_cases))
        results.append(result)

    if formatter:
        formatter.print_results_summary(results, test_type, URL, start_time)

    return results


def _create_pytest_test_function(test_cases: List[Dict[str, Any]], test_type: str):
    """Create a pytest test function for given test cases."""
    async def test_function(request, capfd):
        evaluation_chain = create_evaluation_chain()
        use_formatter = not request.config.getoption("--disable-formatter")

        if use_formatter:
            with capfd.disabled():
                results = await run_test_suite(test_cases, test_type, evaluation_chain, use_formatter)
        else:
            results = await run_test_suite(test_cases, test_type, evaluation_chain, use_formatter)

        failed_tests = [r for r in results if r["status"] == "error"]
        if failed_tests:
            pytest.fail(f"{len(failed_tests)} tests failed")

    return test_function


# Pytest test functions
@pytest.mark.asyncio
async def test_single_dataset_cases(request, capfd):
    """Test single dataset cases."""
    test_function = _create_pytest_test_function(SINGLE_DATASET_TEST_CASES, "single dataset")
    await test_function(request, capfd)


@pytest.mark.asyncio
async def test_multi_dataset_cases(request, capfd):
    """Test multi dataset cases."""
    test_function = _create_pytest_test_function(MULTI_DATASET_TEST_CASES, "multi dataset")
    await test_function(request, capfd)


@pytest.mark.asyncio
async def test_all_cases(request, capfd):
    """Test all cases."""
    all_cases = SINGLE_DATASET_TEST_CASES + MULTI_DATASET_TEST_CASES
    test_function = _create_pytest_test_function(all_cases, "all")
    await test_function(request, capfd)


# Utility functions for standalone execution
async def run_tests(
    test_type: str = "all",
    server_url: str = "http://localhost:8001/api/v1/chat/completions"
) -> List[Dict[str, Any]]:
    """Run test cases against the conversational AI server."""
    global URL
    URL = server_url

    start_time = datetime.now()
    formatter = TerminalFormatter(use_colors=True)
    formatter.print_framework_header(start_time)

    chain = create_evaluation_chain()
    test_cases = get_test_cases(SINGLE_DATASET_TEST_CASES, MULTI_DATASET_TEST_CASES, test_type)
    results = []

    formatter.print_test_suite_info(len(test_cases), test_type, server_url)

    for i, query in enumerate(test_cases, 1):
        result = await process_test_case(query, chain, formatter, i, len(test_cases))
        results.append(result)

    formatter.print_results_summary(results, test_type, server_url, start_time)
    return results


# Main execution
if __name__ == "__main__":
    asyncio.run(run_tests(test_type="multi"))
