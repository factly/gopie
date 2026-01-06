from datetime import datetime
from typing import Any

import pytest

from tests.e2e.utils.dataset_manager import (
    cleanup_project,
    setup_project_and_upload_datasets,
)
from tests.e2e.utils.generate_app_cases import generate_app_cases
from tests.test_config import TestConfig

from .utils.terminal_formatter import TerminalFormatter
from .utils.test_utils import (
    create_evaluation_chain,
    get_user_query,
    handle_expected_error,
    initialize_test_results,
    send_chat_request,
    update_results_with_evaluation,
)

CHAT_SERVER_URL = TestConfig.CHAT_SERVER_URL
GOPIE_API_URL = TestConfig.GOPIE_API_URL


async def process_test_case(
    test_case: dict[str, Any],
    evaluation_chain,
    url: str,
    formatter: TerminalFormatter | None = None,
    test_num: int | None = None,
    total_tests: int | None = None,
) -> dict[str, Any]:
    user_query = get_user_query(test_case)

    if formatter and test_num and total_tests:
        formatter.print_test_case_header(test_num, total_tests, user_query)

    expected_result = test_case.get("expected_result", "")
    results = initialize_test_results(user_query, expected_result)

    try:
        if formatter:
            formatter.print_processing_status("Processing query...")

        response = await send_chat_request(test_case, url)

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
    test_cases: list[dict],
    test_type: str,
    evaluation_chain,
    url: str,
    use_formatter: bool = True,
) -> list[dict]:
    start_time = datetime.now()
    formatter = TerminalFormatter(use_colors=True) if use_formatter else None

    if formatter:
        formatter.print_framework_header(start_time)
        formatter.print_test_suite_info(len(test_cases), test_type, url)

    results = []
    for i, test_case in enumerate(test_cases, 1):
        result = await process_test_case(
            test_case, evaluation_chain, url, formatter, i, len(test_cases)
        )
        results.append(result)

    if formatter:
        formatter.print_results_summary(results, test_type, url, start_time)

    return results


@pytest.mark.asyncio
async def test_app_e2e(request, capfd):
    test_type = request.config.getoption("--type", default="all").lower()
    use_formatter = not request.config.getoption("--disable-formatter", default=False)

    evaluation_chain = create_evaluation_chain()
    project_id = setup_project_and_upload_datasets(gopie_url=GOPIE_API_URL)

    results = []

    try:
        if use_formatter:
            with capfd.disabled():
                print(f"Project ID for this test run: {project_id}")
                test_cases = await generate_app_cases(test_type, [project_id], GOPIE_API_URL)
                results = await run_test_suite(
                    test_cases, test_type, evaluation_chain, CHAT_SERVER_URL, use_formatter
                )
        else:
            test_cases = await generate_app_cases(test_type, [project_id], GOPIE_API_URL)
            results = await run_test_suite(
                test_cases, test_type, evaluation_chain, CHAT_SERVER_URL, use_formatter
            )

        failed_tests = [r for r in results if r["status"] == "error"]
        if failed_tests:
            pytest.fail(f"{len(failed_tests)} tests failed")

    finally:
        if project_id:
            with capfd.disabled():
                print(f"\n\nCleaning up project {project_id}...")
                cleanup_project(gopie_url=GOPIE_API_URL, project_id=project_id)
