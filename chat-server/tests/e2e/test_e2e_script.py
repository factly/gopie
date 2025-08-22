from datetime import datetime
from typing import Any, Dict, List, Optional

import pytest

from .dataset_test_cases import (
    MULTI_DATASET_TEST_CASES,
    SINGLE_DATASET_TEST_CASES,
    VISUALIZATION_TEST_CASES,
)
from .terminal_formatter import TerminalFormatter
from .test_utils import (
    create_evaluation_chain,
    get_user_query,
    handle_expected_error,
    initialize_test_results,
    send_chat_request,
    update_results_with_evaluation,
)

URL = "http://localhost:8000/api/v1/chat/completions"


async def process_test_case(
    test_case: Dict[str, Any],
    evaluation_chain,
    formatter: Optional[TerminalFormatter] = None,
    test_num: Optional[int] = None,
    total_tests: Optional[int] = None,
) -> Dict[str, Any]:
    user_query = get_user_query(test_case)

    if formatter and test_num and total_tests:
        formatter.print_test_case_header(test_num, total_tests, user_query)

    expected_result = test_case.get("expected_result", "")
    results = initialize_test_results(user_query, expected_result)

    try:
        if formatter:
            formatter.print_processing_status("Processing query...")

        response = await send_chat_request(test_case, URL)

        if "error" in response:
            # Check if this is an expected error test case
            if isinstance(expected_result, dict) and (
                expected_result.get("error_expected") or expected_result.get("execution_failure")
            ):
                return handle_expected_error(results, formatter)
            else:
                raise Exception(response["error"])

        # Check if we expected an error but didn't get one
        if isinstance(expected_result, dict) and (
            expected_result.get("error_expected") or expected_result.get("execution_failure")
        ):
            raise Exception("Expected error but API call succeeded")

        if formatter:
            formatter.print_response_summary(
                response["final_response"],
                response["selected_datasets"],
                response["generated_sql_queries"],
                response["tool_messages"],
                response.get("visualization_results", []),
            )
            formatter.print_evaluation_status()

        # For string expected results, use them directly for evaluation
        evaluation_input = expected_result if isinstance(expected_result, str) else expected_result

        comprehensive_response = {
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

        evaluation = await evaluation_chain.ainvoke(
            {
                "generated_answer": comprehensive_response,
                "expected_result": evaluation_input,
            }
        )

        update_results_with_evaluation(results, evaluation, response, expected_result, formatter)
        return results

    except Exception as e:
        if formatter:
            formatter.print_error(f"Test failed: {str(e)}")

        results.update({"reasoning": f"Error: {str(e)}", "error": str(e), "status": "error"})
        return results


async def run_test_suite(
    test_cases: List[Dict[str, Any]], test_type: str, evaluation_chain, use_formatter: bool = True
) -> List[Dict[str, Any]]:
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
    async def test_function(request, capfd):
        evaluation_chain = create_evaluation_chain()
        use_formatter = not request.config.getoption("--disable-formatter", default=False)

        if use_formatter:
            with capfd.disabled():
                results = await run_test_suite(
                    test_cases, test_type, evaluation_chain, use_formatter
                )
        else:
            results = await run_test_suite(test_cases, test_type, evaluation_chain, use_formatter)

        failed_tests = [r for r in results if r["status"] == "error"]
        if failed_tests:
            pytest.fail(f"{len(failed_tests)} tests failed")

    return test_function


@pytest.mark.asyncio
async def test_single_dataset_cases(request, capfd):
    test_function = _create_pytest_test_function(SINGLE_DATASET_TEST_CASES, "single dataset")
    await test_function(request, capfd)


@pytest.mark.asyncio
async def test_visualization_cases(request, capfd):
    test_function = _create_pytest_test_function(VISUALIZATION_TEST_CASES, "visualization")
    await test_function(request, capfd)


@pytest.mark.asyncio
async def test_multi_dataset_cases(request, capfd):
    test_function = _create_pytest_test_function(MULTI_DATASET_TEST_CASES, "multi dataset")
    await test_function(request, capfd)


@pytest.mark.asyncio
async def test_all_cases(request, capfd):
    all_cases = SINGLE_DATASET_TEST_CASES + MULTI_DATASET_TEST_CASES + VISUALIZATION_TEST_CASES
    test_function = _create_pytest_test_function(all_cases, "all")
    await test_function(request, capfd)


if __name__ == "__main__":
    print("Use pytest to run the tests:")
    print("pytest tests/e2e/test_e2e_script.py::test_single_dataset_cases -v")
    print("pytest tests/e2e/test_e2e_script.py::test_multi_dataset_cases -v")
    print("pytest tests/e2e/test_e2e_script.py::test_visualization_cases -v")
    print("pytest tests/e2e/test_e2e_script.py::test_all_cases -v")
